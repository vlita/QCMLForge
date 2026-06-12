import importlib.util
from pathlib import Path

import pandas as pd
import qcelemental as qcel


WORKDIR = Path(__file__).resolve().parent
GEOM_PATH = Path(
    "/home/vlita3/QCMLForge/tests/test_data_path/test_geoms/one_geom/benzene_dimer.dat"
)
MANYBODY_PATH = Path("/home/vlita3/QCMLForge/src/qcml_mcp/run-IEs/example_manybody.py")
LEVEL_OF_THEORY = "PBE-D3/cc-pVDZ/unCP"


def load_manybody_module():
    spec = importlib.util.spec_from_file_location("example_manybody", MANYBODY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    raw = GEOM_PATH.read_text(encoding="utf-8", errors="ignore")
    mol = qcel.models.Molecule.from_data(raw)
    df = pd.DataFrame(
        [
            {
                "id": GEOM_PATH.stem,
                "n_atoms": len(mol.atomic_numbers),
                "Level of Theory": LEVEL_OF_THEORY,
                "qcel_dimer": mol,
            }
        ]
    )
    if len(df) != 1:
        raise RuntimeError(f"Refusing to queue {len(df)} records; expected exactly 1")

    manybody = load_manybody_module()
    queued = manybody.queue_manybodys(df)
    if len(queued) != 1:
        raise RuntimeError(f"Queued dataframe has {len(queued)} records; expected exactly 1")

    queued.to_pickle(WORKDIR / "phoenix_single_test_queued.pkl", protocol=2)
    queued.drop(columns=["qcel_dimer"], errors="ignore").to_csv(
        WORKDIR / "phoenix_single_test_queued.csv", index=False
    )
    print(
        queued[["id", "Level of Theory", "qcfractal id", "job status"]].to_string(
            index=False
        )
    )
    manybody.check_manybody_progress(queued, max_print=1)


if __name__ == "__main__":
    main()
