import importlib.util
from pathlib import Path

import pandas as pd
import qcelemental as qcel


WORKDIR = Path(__file__).resolve().parent
MANYBODY_PATH = Path("/home/vlita3/QCMLForge/src/qcml_mcp/run-IEs/example_manybody.py")
BUDGET_SECONDS = 2.5 * 60 * 60


def load_manybody_module():
    spec = importlib.util.spec_from_file_location("example_manybody", MANYBODY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_qcel_molecule(geom_path: str):
    with open(geom_path, "r", encoding="utf-8", errors="ignore") as handle:
        return qcel.models.Molecule.from_data(handle.read())


def main() -> None:
    all_df = pd.read_pickle(WORKDIR / "all_lots_predictions_no_mols.pkl")
    excluded = all_df[all_df["walltime_seconds"] > BUDGET_SECONDS].copy()
    excluded = excluded.reset_index(drop=True)
    excluded.to_pickle(WORKDIR / "run_ies_excluded_input.pkl", protocol=2)

    geom_index = pd.read_csv(WORKDIR / "geom_index.csv")
    mol_map = {
        row["id"]: parse_qcel_molecule(row["geom_path"])
        for _, row in geom_index.iterrows()
    }
    excluded["qcel_dimer"] = excluded["id"].map(mol_map)

    manybody = load_manybody_module()
    queued_excluded = manybody.queue_manybodys(excluded)
    queued_excluded.to_pickle(WORKDIR / "run_ies_queued_excluded.pkl", protocol=2)
    queued_excluded.drop(columns=["qcel_dimer"], errors="ignore").to_csv(
        WORKDIR / "run_ies_queued_excluded_summary.csv", index=False
    )

    queued_budget = pd.read_pickle(WORKDIR / "run_ies_queued.pkl")
    queued_all = pd.concat([queued_budget, queued_excluded], ignore_index=True)
    queued_all.to_pickle(WORKDIR / "run_ies_queued_all.pkl", protocol=2)
    queued_all.drop(columns=["qcel_dimer"], errors="ignore").to_csv(
        WORKDIR / "run_ies_queued_all_summary.csv", index=False
    )

    print("submitted_excluded_jobs", len(queued_excluded))
    print("combined_jobs", len(queued_all))
    print(
        queued_excluded[
            [
                "id",
                "Level of Theory",
                "qcfractal id",
                "walltime_seconds",
                "ESTIMATED CPU TIMES (log10(s))",
            ]
        ]
    )
    manybody.check_manybody_progress(queued_excluded, max_print=9)


if __name__ == "__main__":
    main()
