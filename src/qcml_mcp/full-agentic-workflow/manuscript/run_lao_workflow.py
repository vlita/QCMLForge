"""Run the full-agentic workflow for the Lao (2024) large dimers.

Run `phase1` with the qcml Python environment, and the QCFractal phases with
the p4_qcml Python environment.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import qcelemental as qcel


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
GEOM_DIR = REPO / "tests/test_data_path/test_geoms/Large_dimers"
REF_PATH = ROOT / "reference_l14_ccsdt_cbs.csv"
METHODS = ["HF", "PBE-D3", "wB97X-D", "wB97X-V", "MP2", "B3LYP-D3", "B2PLYP-D3"]
BASES = ["aug-cc-pVTZ"]
H2KCALMOL = 627.509


def _level_sort_key(level: str) -> tuple[int, str]:
    method = level.split("/")[0]
    return (METHODS.index(method) if method in METHODS else len(METHODS), level)


def _normalize_qcf_id(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _geometry_index() -> pd.DataFrame:
    rows = []
    for path in sorted(GEOM_DIR.glob("*.xyz")):
        rows.append({"id": path.stem, "geom_path": str(path)})
    return pd.DataFrame(rows)


def _read_molecule(path: str):
    return qcel.models.Molecule.from_data(Path(path).read_text())


def _attach_molecules(df: pd.DataFrame) -> pd.DataFrame:
    geom_index = pd.read_csv(ROOT / "geom_index.csv")
    mol_map = {row.id: _read_molecule(row.geom_path) for row in geom_index.itertuples()}
    df = df.copy()
    df["qcel_dimer"] = df["id"].map(mol_map)
    return df


def _parse_status(status) -> str:
    text = str(status)
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return text.lower()


def _load_example_manybody():
    path = REPO / "src/qcml_mcp/run-IEs/example_manybody.py"
    spec = importlib.util.spec_from_file_location("example_manybody", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def phase1(args: argparse.Namespace) -> None:
    from qcml_mcp.ie_time_esimator_script import main

    df = main(
        geom_path=str(GEOM_DIR),
        methods=METHODS,
        bases=BASES,
        using_cp=True,
        auto_download=True,
    )
    df["walltime_seconds"] = 10 ** df["ESTIMATED CPU TIMES (log10(s))"]
    df.to_pickle(ROOT / "select_lot_df.pkl")
    df.to_csv(ROOT / "select_lot_df.csv", index=False)

    feasible = df[df["walltime_seconds"] <= args.budget_seconds].copy()
    if feasible.empty:
        raise RuntimeError(f"No requested levels fit {args.budget_seconds} wall seconds")

    winners = []
    for system_id, group in feasible.groupby("id"):
        best = group.loc[group["ERROR ESTIMATES (kcal/mol)"].abs().idxmin()]
        winners.append({"id": system_id, "Level of Theory": best["Level of Theory"]})
    winners_df = pd.DataFrame(winners)
    counts = winners_df["Level of Theory"].value_counts()
    summaries = []
    for level, group in feasible.groupby("Level of Theory"):
        summaries.append(
            {
                "Level of Theory": level,
                "winner_count": int(counts.get(level, 0)),
                "median_abs_pred_error": float(group["ERROR ESTIMATES (kcal/mol)"].abs().median()),
                "mean_abs_pred_error": float(group["ERROR ESTIMATES (kcal/mol)"].abs().mean()),
                "max_pred_walltime_seconds": float(group["walltime_seconds"].max()),
                "median_pred_walltime_seconds": float(group["walltime_seconds"].median()),
            }
        )
    ranking = pd.DataFrame(summaries).sort_values(
        ["winner_count", "median_abs_pred_error", "median_pred_walltime_seconds"],
        ascending=[False, True, True],
    )
    ranking.to_csv(ROOT / "select_lot_recommendation.csv", index=False)
    winners_df.to_csv(ROOT / "select_lot_system_winners.csv", index=False)

    geom_index = _geometry_index()
    geom_index.to_csv(ROOT / "geom_index.csv", index=False)
    drop_cols = ["qcel_dimer", "qcel_monA", "qcel_monB"]
    df.drop(columns=drop_cols, errors="ignore").to_pickle(ROOT / "run_ies_input.pkl", protocol=2)
    df.drop(columns=drop_cols, errors="ignore").to_csv(ROOT / "run_ies_input.csv", index=False)

    report = {
        "budget_seconds": args.budget_seconds,
        "budget_hours": args.budget_seconds / 3600,
        "n_systems": int(df["id"].nunique()),
        "n_levels": int(df["Level of Theory"].nunique()),
        "n_rows": int(len(df)),
        "n_budget_feasible_rows": int(len(feasible)),
        "recommended_level": ranking.iloc[0]["Level of Theory"],
    }
    (ROOT / "phase1_summary.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


def check_qcf(_: argparse.Namespace) -> None:
    import qcportal

    client = qcportal.PortalClient("http://localhost:7777", verify=False)
    info = client.get_server_information()
    payload = {"connected": True, "server_information": info}
    (ROOT / "qcf_connection.json").write_text(json.dumps(payload, indent=2, default=str))
    print(json.dumps(payload, indent=2, default=str))


def queue(args: argparse.Namespace) -> None:
    import qcportal
    from qcportal.singlepoint import QCSpecification

    client = qcportal.PortalClient("http://localhost:7777", verify=False)
    df = pd.read_pickle(ROOT / "run_ies_input.pkl")
    if args.only_within_budget:
        df = df[df["walltime_seconds"] <= args.budget_seconds].copy()
    df = _attach_molecules(df)
    manybody_ids = []
    for _, row in df.iterrows():
        method, basis, cp_str = row["Level of Theory"].split("/")
        qc_spec = QCSpecification(
            program="psi4",
            driver="energy",
            method=method,
            basis=basis,
        )
        _, ids = client.add_manybodys(
            [row["qcel_dimer"]],
            program="qcmanybody",
            levels={1: qc_spec, 2: qc_spec},
            bsse_correction=["nocp" if "un" in cp_str.lower() else "cp"],
            tag="phoenix-agent",
            keywords={},
            find_existing=False,
        )
        manybody_ids.append(ids)
    queued = df.copy()
    queued["qcfractal id"] = manybody_ids
    queued["job status"] = np.nan
    queued["mb_interaction_energy"] = np.nan
    queued["mb_wall_time"] = np.nan
    queued["psi4 output"] = None
    queued["submitted_unix_time"] = time.time()
    queued.drop(columns=["qcel_dimer"], errors="ignore").to_pickle(ROOT / "run_ies_queued.pkl", protocol=2)
    queued.drop(columns=["qcel_dimer"], errors="ignore").to_csv(ROOT / "run_ies_queued.csv", index=False)
    print(f"queued {len(queued)} manybody records")


def requeue_failed(args: argparse.Namespace) -> None:
    import qcportal
    from qcportal.singlepoint import QCSpecification

    source = ROOT / "full_workflow_results.pkl"
    if not source.exists():
        source = ROOT / "run_ies_results.pkl"
    df = pd.read_pickle(source).copy()
    failed = df[df["job status"].astype(str).str.lower() == "error"].copy()
    if failed.empty:
        print("no failed computations to requeue")
        return

    client = qcportal.PortalClient("http://localhost:7777", verify=False)
    failed = _attach_molecules(failed.drop(columns=["qcel_dimer"], errors="ignore"))

    old_ids = failed["qcfractal id"].tolist()
    new_ids = []
    for _, row in failed.iterrows():
        method, basis, cp_str = row["Level of Theory"].split("/")
        qc_spec = QCSpecification(
            program="psi4",
            driver="energy",
            method=method,
            basis=basis,
        )
        _, ids = client.add_manybodys(
            [row["qcel_dimer"]],
            program="qcmanybody",
            levels={1: qc_spec, 2: qc_spec},
            bsse_correction=["nocp" if "un" in cp_str.lower() else "cp"],
            tag="phoenix-agent",
            keywords={},
            find_existing=False,
        )
        new_ids.append(ids)

    failed["old qcfractal id"] = old_ids
    failed["qcfractal id"] = new_ids
    failed["job status"] = np.nan
    failed["mb_interaction_energy"] = np.nan
    failed["mb_wall_time"] = np.nan
    failed["psi4 output"] = None
    failed["submitted_unix_time"] = time.time()
    failed.drop(columns=["qcel_dimer"], errors="ignore").to_pickle(
        ROOT / "run_ies_failed_requeued.pkl", protocol=2
    )
    failed.drop(columns=["qcel_dimer"], errors="ignore").to_csv(
        ROOT / "run_ies_failed_requeued.csv", index=False
    )
    print(f"requeued {len(failed)} failed manybody records")


def status(_: argparse.Namespace) -> None:
    import qcportal

    client = qcportal.PortalClient("http://localhost:7777", verify=False)
    df = pd.read_pickle(ROOT / "run_ies_queued.pkl")
    ids = [_normalize_qcf_id(v) for v in df["qcfractal id"].tolist()]
    recs = client.get_manybodys(ids, include=["clusters"])
    rows = []
    for (_, row), rec in zip(df.iterrows(), recs):
        rows.append(
            {
                "id": row["id"],
                "Level of Theory": row["Level of Theory"],
                "qcfractal_id": _normalize_qcf_id(row["qcfractal id"]),
                "status": _parse_status(rec.status) if rec else "missing",
                "n_clusters": len(rec.clusters or []) if rec else 0,
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "qcf_status.csv", index=False)
    print(out["status"].value_counts().to_string())


def _extract_interaction_energy(rec, level: str) -> float:
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


def retrieve(_: argparse.Namespace) -> None:
    import qcportal

    client = qcportal.PortalClient("http://localhost:7777", verify=False)
    df = pd.read_pickle(ROOT / "run_ies_queued.pkl").copy().reset_index(drop=True)
    ids = [_normalize_qcf_id(v) for v in df["qcfractal id"].tolist()]
    recs = client.get_manybodys(ids, include=["clusters", "**"])
    output_dir = ROOT / "psi4_outputs"
    output_dir.mkdir(exist_ok=True)
    manifest = []

    for idx, rec in zip(df.index, recs):
        if rec is None:
            df.at[idx, "job status"] = "missing"
            continue
        status_text = _parse_status(rec.status)
        df.at[idx, "job status"] = status_text
        df.at[idx, "mb_interaction_energy"] = _extract_interaction_energy(
            rec, df.at[idx, "Level of Theory"]
        )
        if rec.compute_history and rec.compute_history[-1].provenance:
            df.at[idx, "mb_wall_time"] = getattr(
                rec.compute_history[-1].provenance, "wall_time", np.nan
            )

        for cluster in rec.clusters or []:
            sp = cluster.singlepoint_record
            if sp is None:
                continue
            safe_level = df.at[idx, "Level of Theory"].replace("/", "_")
            prefix = f"{safe_level}__{df.at[idx, 'id']}__mbid_{rec.id}__spid_{sp.id}"
            for attr in ("stdout", "stderr"):
                text = getattr(sp, attr, None)
                if text:
                    path = output_dir / f"{prefix}.{attr}.txt"
                    path.write_text(text)
                    manifest.append(str(path.relative_to(ROOT)))

    df.to_pickle(ROOT / "run_ies_results.pkl", protocol=2)
    df.to_csv(ROOT / "run_ies_results.csv", index=False)
    (output_dir / "MANIFEST.txt").write_text("\n".join(manifest) + ("\n" if manifest else ""))
    print(df["job status"].value_counts(dropna=False).to_string())


def retrieve_requeued_failed(_: argparse.Namespace) -> None:
    import qcportal

    client = qcportal.PortalClient("http://localhost:7777", verify=False)
    retry_path = ROOT / "run_ies_failed_requeued.pkl"
    retry = pd.read_pickle(retry_path).copy().reset_index(drop=True)
    ids = [_normalize_qcf_id(v) for v in retry["qcfractal id"].tolist()]
    recs = client.get_manybodys(ids, include=["clusters", "**"])

    for idx, rec in zip(retry.index, recs):
        if rec is None:
            retry.at[idx, "job status"] = "missing"
            continue
        status_text = _parse_status(rec.status)
        retry.at[idx, "job status"] = status_text
        retry.at[idx, "mb_interaction_energy"] = _extract_interaction_energy(
            rec, retry.at[idx, "Level of Theory"]
        )
        if rec.compute_history and rec.compute_history[-1].provenance:
            retry.at[idx, "mb_wall_time"] = getattr(
                rec.compute_history[-1].provenance, "wall_time", np.nan
            )

    retry.to_pickle(ROOT / "run_ies_failed_retry_results.pkl", protocol=2)
    retry.to_csv(ROOT / "run_ies_failed_retry_results.csv", index=False)

    base = pd.read_pickle(ROOT / "run_ies_results.pkl").copy().reset_index(drop=True)
    for _, row in retry.iterrows():
        if row["job status"] != "complete":
            continue
        mask = (base["id"] == row["id"]) & (
            base["Level of Theory"] == row["Level of Theory"]
        )
        for col in [
            "qcfractal id",
            "job status",
            "mb_interaction_energy",
            "mb_wall_time",
            "psi4 output",
        ]:
            if col in base.columns and col in retry.columns:
                base.loc[mask, col] = [row[col]] * int(mask.sum())
    base.to_pickle(ROOT / "run_ies_results_merged.pkl", protocol=2)
    base.to_csv(ROOT / "run_ies_results_merged.csv", index=False)
    print("retry results")
    print(retry["job status"].value_counts(dropna=False).to_string())
    print("merged results")
    print(base["job status"].value_counts(dropna=False).to_string())


def postprocess(_: argparse.Namespace) -> None:
    results_path = ROOT / "run_ies_results_merged.pkl"
    if not results_path.exists():
        results_path = ROOT / "run_ies_results.pkl"
    df = pd.read_pickle(results_path).copy()
    refs = pd.read_csv(REF_PATH)
    df["mb_ie_kcalmol"] = df["mb_interaction_energy"] * H2KCALMOL
    df["ERROR ESTIMATES (kcal/mol)"] = -df["ERROR ESTIMATES (kcal/mol)"]
    df = df.merge(refs, on="id", how="left")
    df["IE_error_kcalmol"] = (df["mb_ie_kcalmol"] - df["reference_ie"]).round(2)
    df = df.drop(columns=["abs_IE_error_kcalmol"], errors="ignore")
    df.to_pickle(ROOT / "full_workflow_results.pkl", protocol=2)
    df.to_csv(ROOT / "full_workflow_results.csv", index=False)

    by_level = []
    for level, group in df.groupby("Level of Theory"):
        abs_errors = group["IE_error_kcalmol"].abs()
        by_level.append(
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
    summary = pd.DataFrame(by_level).sort_values(
        ["mean_abs_error", "median_abs_error"], ascending=[True, True]
    )
    summary.to_csv(ROOT / "final_lot_ranking_lao.csv", index=False)

    phase1_summary = json.loads((ROOT / "phase1_summary.json").read_text())
    recommended = phase1_summary["recommended_level"]
    rec_rows = df[df["Level of Theory"] == recommended].copy()
    rec_rows.sort_values("id").to_csv(ROOT / "recommended_level_errors.csv", index=False)
    print(summary.to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "phase",
        choices=[
            "phase1",
            "check-qcf",
            "queue",
            "requeue-failed",
            "status",
            "retrieve",
            "retrieve-requeued-failed",
            "postprocess",
        ],
    )
    parser.add_argument("--budget-seconds", type=float, default=2.5 * 3600)
    parser.add_argument("--only-within-budget", action="store_true")
    args = parser.parse_args()
    globals()[args.phase.replace("-", "_")](args)


if __name__ == "__main__":
    main()
