import importlib.util
from pathlib import Path

import pandas as pd
import qcelemental as qcel


WORKDIR = Path(__file__).resolve().parent
MANYBODY_PATH = Path("/home/vlita3/QCMLForge/src/qcml_mcp/run-IEs/example_manybody.py")


def load_manybody_module():
    spec = importlib.util.spec_from_file_location("example_manybody", MANYBODY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_qcel_molecule(geom_path: str):
    with open(geom_path, "r", encoding="utf-8", errors="ignore") as handle:
        return qcel.models.Molecule.from_data(handle.read())


def main() -> None:
    df = pd.read_pickle(WORKDIR / "run_ies_input.pkl")
    geom_index = pd.read_csv(WORKDIR / "geom_index.csv")
    mol_map = {
        row["id"]: parse_qcel_molecule(row["geom_path"])
        for _, row in geom_index.iterrows()
    }
    df["qcel_dimer"] = df["id"].map(mol_map)

    manybody = load_manybody_module()
    queued = manybody.queue_manybodys(df)
    queued.to_pickle(WORKDIR / "run_ies_queued.pkl", protocol=2)
    queued.drop(columns=["qcel_dimer"], errors="ignore").to_csv(
        WORKDIR / "run_ies_queued_summary.csv", index=False
    )

    print("submitted_jobs", len(queued))
    print(
        queued[
            [
                "id",
                "Level of Theory",
                "qcfractal id",
                "walltime_seconds",
                "ESTIMATED CPU TIMES (log10(s))",
            ]
        ]
    )
    manybody.check_manybody_progress(queued, max_print=10)


if __name__ == "__main__":
    main()
