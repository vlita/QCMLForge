import os
from pathlib import Path

import pandas as pd

from qcml_mcp.ie_time_esimator_script import main


WORKDIR = Path(__file__).resolve().parent
GEOM_DIR = Path("/home/vlita3/QCMLForge/tests/test_data_path/test_geoms/Large_dimers")
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


def main_phase1() -> None:
    os.chdir(WORKDIR)
    df = main(
        geom_path=str(GEOM_DIR),
        methods=METHODS,
        bases=BASES,
        using_cp=True,
        auto_download=True,
    )
    df = df.reset_index(drop=True)
    df["walltime_seconds"] = 10 ** df["ESTIMATED CPU TIMES (log10(s))"]
    df.to_pickle(WORKDIR / "select_lot_df.pkl")

    feasible = df[df["walltime_seconds"] <= BUDGET_SECONDS].copy()
    feasible.to_pickle(WORKDIR / "run_ies_input_with_mols.pkl")

    if feasible.empty:
        recommendation = pd.DataFrame()
    else:
        winner_idx = feasible.groupby("id")["ERROR ESTIMATES (kcal/mol)"].apply(
            lambda s: s.abs().idxmin()
        )
        winners = feasible.loc[winner_idx]
        summary = (
            winners.groupby("Level of Theory")
            .size()
            .rename("wins")
            .to_frame()
            .join(
                feasible.assign(abs_error=feasible["ERROR ESTIMATES (kcal/mol)"].abs())
                .groupby("Level of Theory")
                .agg(
                    median_abs_error=("abs_error", "median"),
                    median_walltime_seconds=("walltime_seconds", "median"),
                )
            )
            .sort_values(["wins", "median_abs_error", "median_walltime_seconds"], ascending=[False, True, True])
        )
        recommendation = summary

    recommendation.to_csv(WORKDIR / "select_lot_recommendation.csv")

    geom_index = pd.DataFrame(
        {
            "id": [path.stem for path in sorted(GEOM_DIR.iterdir()) if path.is_file()],
            "geom_path": [str(path) for path in sorted(GEOM_DIR.iterdir()) if path.is_file()],
        }
    )
    geom_index.to_csv(WORKDIR / "geom_index.csv", index=False)

    sub_df = feasible.drop(columns=["qcel_dimer", "qcel_monA", "qcel_monB"], errors="ignore")
    sub_df.to_pickle(WORKDIR / "run_ies_input.pkl", protocol=2)

    full_sub_df = df.drop(columns=["qcel_dimer", "qcel_monA", "qcel_monB"], errors="ignore")
    full_sub_df.to_pickle(WORKDIR / "all_lots_predictions_no_mols.pkl", protocol=2)

    print("budget_seconds", BUDGET_SECONDS)
    print("total_rows", len(df))
    print("feasible_rows", len(feasible))
    print("feasible_lots", sorted(feasible["Level of Theory"].unique().tolist()))
    if not recommendation.empty:
        print("recommended_lot", recommendation.index[0])
        print(recommendation)


if __name__ == "__main__":
    main_phase1()
