import importlib.util
import os
from pathlib import Path

import pandas as pd


REPO_ROOT = Path("/home/vlita3/QCMLForge")
WORKDIR = REPO_ROOT / "src/qcml_mcp/full-agentic-workflow/agent_workflow_example"
GEOM_DIR = REPO_ROOT / "tests/test_data_path/test_geoms/Large_dimers"
BUDGET_SECONDS = 2.5 * 60 * 60

METHODS = [
    "HF",
    "PBE-D3",
    "wB97X-D",
    "wB97X-V",
    "MP2",
    "B3LYP-D3",
    "B2PLYP-D3",
]
BASES = ["aug-cc-pVTZ"]
REFERENCES = {
    "C2C2PD": -20.65,
    "C3A": -16.34,
    "CBH": -11.06,
    "2a": -34.15,
    "S8-2": -30.79,
    "Da2": -20.20,
}


def bucket(percent_error):
    if percent_error < 2:
        return "high_accuracy"
    if percent_error < 5:
        return "medium_accuracy"
    if percent_error < 10:
        return "low_accuracy"
    return "not_recommended"


def main():
    os.chdir(WORKDIR)
    script_path = REPO_ROOT / "src/qcml_mcp/ie_time_esimator_script.py"
    spec = importlib.util.spec_from_file_location("ie_time_esimator_script", script_path)
    lot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lot)

    df = lot.main(
        geom_path=str(GEOM_DIR),
        methods=METHODS,
        bases=BASES,
        using_cp=True,
        auto_download=True,
    )
    df["predicted_ie_error_kcalmol_for_bucketing"] = -df[
        "ERROR ESTIMATES (kcal/mol)"
    ]
    df["walltime_seconds"] = 10 ** df["ESTIMATED CPU TIMES (log10(s))"]
    df["reference_ie"] = df["id"].map(REFERENCES)
    missing = sorted(df.loc[df["reference_ie"].isna(), "id"].unique())
    if missing:
        raise ValueError(f"Missing reference energies for: {missing}")
    if (df["reference_ie"].abs() < 1e-12).any():
        raise ValueError("Near-zero reference interaction energy encountered")

    df["predicted_abs_percent_error"] = (
        100
        * df["predicted_ie_error_kcalmol_for_bucketing"].abs()
        / df["reference_ie"].abs()
    )
    df["accuracy_bucket"] = df["predicted_abs_percent_error"].map(bucket)
    df.to_pickle(WORKDIR / "select_lot_df.pkl")

    feasible = df[df["walltime_seconds"] <= BUDGET_SECONDS].copy()
    feasible.to_pickle(WORKDIR / "select_lot_feasible_df.pkl")

    geom_index = pd.DataFrame(
        {
            "id": [p.stem for p in sorted(GEOM_DIR.iterdir()) if p.is_file()],
            "geom_path": [str(p) for p in sorted(GEOM_DIR.iterdir()) if p.is_file()],
        }
    )
    geom_index.to_csv(WORKDIR / "geom_index.csv", index=False)

    sub_df = df.drop(columns=["qcel_dimer", "qcel_monA", "qcel_monB"], errors="ignore")
    sub_df.to_pickle(WORKDIR / "run_ies_input.pkl", protocol=2)
    feasible_sub_df = feasible.drop(
        columns=["qcel_dimer", "qcel_monA", "qcel_monB"], errors="ignore"
    )
    feasible_sub_df.to_pickle(WORKDIR / "run_ies_feasible_input.pkl", protocol=2)

    summary = (
        feasible.groupby(["Level of Theory", "accuracy_bucket"])
        .size()
        .unstack(fill_value=0)
    )
    for col in ["high_accuracy", "medium_accuracy", "low_accuracy", "not_recommended"]:
        if col not in summary.columns:
            summary[col] = 0
    summary["median_predicted_abs_percent_error"] = feasible.groupby("Level of Theory")[
        "predicted_abs_percent_error"
    ].median()
    summary = summary[
        [
            "high_accuracy",
            "medium_accuracy",
            "low_accuracy",
            "not_recommended",
            "median_predicted_abs_percent_error",
        ]
    ].sort_values("median_predicted_abs_percent_error")
    summary.to_csv(WORKDIR / "phase1_bucket_summary.csv")

    per_system = feasible[
        [
            "id",
            "Level of Theory",
            "reference_ie",
            "predicted_ie_error_kcalmol_for_bucketing",
            "predicted_abs_percent_error",
            "accuracy_bucket",
            "walltime_seconds",
        ]
    ].sort_values(["Level of Theory", "id"])
    per_system.to_csv(WORKDIR / "phase1_per_system_buckets.csv", index=False)

    print("FULL_ROWS", len(df))
    print("FEASIBLE_ROWS", len(feasible))
    print(summary)


if __name__ == "__main__":
    main()
