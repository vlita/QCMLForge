"""Refresh final Lao workflow results without queueing new computations."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import qcportal


ROOT = Path(__file__).resolve().parent
H2KCALMOL = 627.509
METHODS = ["HF", "PBE-D3", "wB97X-D", "wB97X-V", "MP2", "B3LYP-D3", "B2PLYP-D3"]


def normalize_id(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def status_text(status) -> str:
    text = str(status)
    return text.rsplit(".", 1)[-1].lower()


def extract_interaction_energy(rec, level: str) -> float:
    props = rec.properties or {}
    bsse = "cp" if level.lower().endswith("/cp") else "nocp"
    candidates = [
        f"{bsse}_corrected_interaction_energy",
        f"{bsse}_interaction_energy",
        "interaction_energy",
    ]
    for key in candidates:
        if key in props:
            return props[key]
    results = props.get("results")
    if isinstance(results, dict):
        for key in candidates:
            if key in results:
                return results[key]
    ies = props.get("interaction_energies")
    if isinstance(ies, dict):
        if bsse in ies:
            return ies[bsse]
        if len(ies) == 1:
            return next(iter(ies.values()))
    return math.nan


def latest_retry_ids() -> dict[tuple[str, str], object]:
    path = ROOT / "run_ies_failed_retry_results.pkl"
    if not path.exists():
        return {}
    retry = pd.read_pickle(path)
    return {
        (row["id"], row["Level of Theory"]): row["qcfractal id"]
        for _, row in retry.iterrows()
    }


def main() -> None:
    final = pd.read_pickle(ROOT / "full_workflow_results.pkl").copy()
    select = pd.read_csv(ROOT / "select_lot_df.csv").drop(
        columns=["qcel_dimer", "qcel_monA", "qcel_monB"], errors="ignore"
    )
    refs = pd.read_csv(ROOT / "reference_l14_ccsdt_cbs.csv")

    keep_actual = [
        "id",
        "Level of Theory",
        "qcfractal id",
        "submitted_unix_time",
        "psi4 output",
    ]
    actual = final[keep_actual].copy()
    for key, qcf_id in latest_retry_ids().items():
        mask = (actual["id"] == key[0]) & (actual["Level of Theory"] == key[1])
        actual.loc[mask, "qcfractal id"] = [qcf_id] * int(mask.sum())

    df = select.merge(actual, on=["id", "Level of Theory"], how="left")
    client = qcportal.PortalClient("http://localhost:7777", verify=False)
    ids = [normalize_id(v) for v in df["qcfractal id"].tolist()]
    records = client.get_manybodys([i for i in ids if i is not None], include=["clusters", "**"])
    record_map = {rec.id: rec for rec in records if rec is not None}

    statuses = []
    energies = []
    for _, row in df.iterrows():
        rec = record_map.get(normalize_id(row["qcfractal id"]))
        if rec is None:
            statuses.append("missing")
            energies.append(np.nan)
            continue
        statuses.append(status_text(rec.status))
        energies.append(extract_interaction_energy(rec, row["Level of Theory"]))

    df["job status"] = statuses
    df["mb_interaction_energy"] = energies
    df["mb_ie_kcalmol"] = df["mb_interaction_energy"] * H2KCALMOL
    df["ERROR ESTIMATES (kcal/mol)"] = -df["ERROR ESTIMATES (kcal/mol)"]
    df = df.merge(refs, on="id", how="left")
    df["IE_error_kcalmol"] = (df["mb_ie_kcalmol"] - df["reference_ie"]).round(2)
    df["walltime_seconds"] = 10 ** df["ESTIMATED CPU TIMES (log10(s))"]

    wall_path = ROOT / "summed_manybody_walltimes.csv"
    if wall_path.exists():
        wall = pd.read_csv(wall_path)
        wall_map = dict(zip(wall["qcfractal_id"], wall["mb_wall_time"]))
        df["mb_wall_time"] = df["qcfractal id"].map(
            lambda value: wall_map.get(normalize_id(value), np.nan)
        )
        df["mb_wall_time_log10_s"] = np.where(
            df["mb_wall_time"] > 0, np.log10(df["mb_wall_time"]), np.nan
        )
        df["mb_wall_time_hours"] = df["mb_wall_time"] / 3600

    df["_method_order"] = df["Level of Theory"].str.split("/").str[0].map(
        {method: idx for idx, method in enumerate(METHODS)}
    )
    df = df.sort_values(["id", "_method_order", "Level of Theory"], kind="stable")
    df = df.drop(columns=["_method_order", "abs_IE_error_kcalmol"], errors="ignore")

    preferred = [
        "id",
        "n_atoms",
        "dimer_tvars",
        "monA_tvars",
        "monB_tvars",
        "Level of Theory",
        "ERROR ESTIMATES (kcal/mol)",
        "ESTIMATED CPU TIMES (log10(s))",
        "walltime_seconds",
        "qcfractal id",
        "job status",
        "mb_interaction_energy",
        "mb_wall_time",
        "mb_wall_time_log10_s",
        "mb_wall_time_hours",
        "psi4 output",
        "submitted_unix_time",
        "mb_ie_kcalmol",
        "reference_ie",
        "IE_error_kcalmol",
    ]
    df = df[[col for col in preferred if col in df.columns]]
    df.to_pickle(ROOT / "full_workflow_results.pkl", protocol=2)
    df.to_csv(ROOT / "full_workflow_results.csv", index=False)

    rows = []
    for level, group in df.groupby("Level of Theory"):
        abs_errors = group["IE_error_kcalmol"].abs()
        rows.append(
            {
                "Level of Theory": level,
                "n_complete": int(group["mb_ie_kcalmol"].notna().sum()),
                "mean_signed_error": float(group["IE_error_kcalmol"].mean()),
                "median_signed_error": float(group["IE_error_kcalmol"].median()),
                "mean_abs_error": float(abs_errors.mean()),
                "median_abs_error": float(abs_errors.median()),
                "max_abs_error": float(abs_errors.max()),
                "median_actual_wall_time": float(group["mb_wall_time"].median()),
                "median_pred_wall_time": float(group["walltime_seconds"].median()),
            }
        )
    summary = pd.DataFrame(rows).sort_values(
        ["mean_abs_error", "median_abs_error"], ascending=[True, True]
    )
    summary.to_csv(ROOT / "final_lot_ranking_lao.csv", index=False)
    print(df["job status"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
