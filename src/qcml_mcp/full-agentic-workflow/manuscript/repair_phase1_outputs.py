from pathlib import Path

import pandas as pd


WORKDIR = Path(__file__).resolve().parent
GEOM_DIR = Path("/home/vlita3/QCMLForge/tests/test_data_path/test_geoms/Large_dimers")
BUDGET_SECONDS = 2.5 * 60 * 60
REFERENCE_IE = {
    "C2C2PD": -20.65,
    "C3A": -16.34,
    "CBH": -11.06,
    "2a": -34.15,
    "S8-2": -30.79,
    "Da2": -20.20,
}


def main() -> None:
    df = pd.read_pickle(WORKDIR / "select_lot_df.pkl").reset_index(drop=True)
    df["walltime_seconds"] = 10 ** df["ESTIMATED CPU TIMES (log10(s))"]
    df.to_pickle(WORKDIR / "select_lot_df.pkl")

    feasible = df[df["walltime_seconds"] <= BUDGET_SECONDS].copy()
    winner_idx = feasible.groupby("id")["ERROR ESTIMATES (kcal/mol)"].apply(
        lambda s: s.abs().idxmin()
    )
    winners = feasible.loc[winner_idx].copy()
    winners.to_csv(WORKDIR / "select_lot_winners_by_system.csv", index=False)

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
    summary.to_csv(WORKDIR / "select_lot_recommendation.csv")

    geom_paths = sorted(path for path in GEOM_DIR.iterdir() if path.is_file())
    geom_index = pd.DataFrame(
        {"id": [path.stem for path in geom_paths], "geom_path": [str(path) for path in geom_paths]}
    )
    geom_index.to_csv(WORKDIR / "geom_index.csv", index=False)

    feasible.drop(columns=["qcel_dimer", "qcel_monA", "qcel_monB"], errors="ignore").to_pickle(
        WORKDIR / "run_ies_input.pkl", protocol=2
    )
    df.drop(columns=["qcel_dimer", "qcel_monA", "qcel_monB"], errors="ignore").to_pickle(
        WORKDIR / "all_lots_predictions_no_mols.pkl", protocol=2
    )
    pd.DataFrame(
        {"id": list(REFERENCE_IE), "reference_ie": list(REFERENCE_IE.values())}
    ).to_csv(WORKDIR / "reference_ie.csv", index=False)

    print("budget_seconds", BUDGET_SECONDS)
    print("total_rows", len(df))
    print("feasible_rows", len(feasible))
    print("recommended_lot", summary.index[0])
    print(summary)
    print("winners_by_system")
    print(winners[["id", "Level of Theory", "ERROR ESTIMATES (kcal/mol)", "walltime_seconds"]])


if __name__ == "__main__":
    main()
