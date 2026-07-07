from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import qcelemental as qcel
import qcportal
from qcportal.singlepoint import QCSpecification


WORKDIR = Path("/home/vlita3/QCMLForge/src/qcml_mcp/full-agentic-workflow/agent_workflow_example")


def parse_molecule(path):
    with open(path, "r", errors="ignore") as handle:
        return qcel.models.Molecule.from_data(handle.read())


def normalize_id(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def main():
    client = qcportal.PortalClient("http://localhost:7777", verify=False)
    df = pd.read_pickle(WORKDIR / "run_ies_input.pkl")
    geom_index = pd.read_csv(WORKDIR / "geom_index.csv")
    mol_map = {
        row["id"]: parse_molecule(row["geom_path"])
        for _, row in geom_index.iterrows()
    }
    df["qcel_dimer"] = df["id"].map(mol_map)

    record_ids = []
    insert_metadata = []
    submission_times = []
    for _, row in df.iterrows():
        method, basis, cp_str = row["Level of Theory"].split("/")
        bsse = "nocp" if ("nocp" in cp_str.lower() or "un" in cp_str.lower()) else "cp"
        qc_spec = QCSpecification(
            program="psi4",
            driver="energy",
            method=method,
            basis=basis,
        )
        meta, ids = client.add_manybodys(
            [row["qcel_dimer"]],
            program="qcmanybody",
            levels={1: qc_spec, 2: qc_spec},
            bsse_correction=[bsse],
            keywords={},
            tag="free",
            find_existing=True,
        )
        record_ids.append(ids)
        insert_metadata.append(str(meta))
        submission_times.append(datetime.now(timezone.utc).isoformat())

    df["qcfractal id"] = record_ids
    df["qcfractal insert metadata"] = insert_metadata
    df["submission_time_utc"] = submission_times
    df["job status"] = pd.NA
    df["mb_interaction_energy"] = pd.NA
    df["mb_wall_time"] = pd.NA
    df["psi4 output"] = None

    ids = [normalize_id(value) for value in df["qcfractal id"].tolist()]
    records = client.get_manybodys(ids, include=["clusters", "**"])
    for idx, rec in enumerate(records):
        if rec is None:
            df.at[idx, "job status"] = "missing"
            continue
        df.at[idx, "job status"] = str(rec.status)

    df.drop(columns=["qcel_dimer"], errors="ignore").to_pickle(
        WORKDIR / "run_ies_queued.pkl", protocol=2
    )
    status_counts = df["job status"].value_counts(dropna=False).rename_axis("status")
    status_counts.to_csv(WORKDIR / "phase3_status_counts.csv")

    status_table = df[
        [
            "id",
            "Level of Theory",
            "walltime_seconds",
            "accuracy_bucket",
            "predicted_abs_percent_error",
            "qcfractal id",
            "job status",
            "submission_time_utc",
        ]
    ].copy()
    status_table.to_csv(WORKDIR / "phase3_queued_status.csv", index=False)

    print("QUEUED_ROWS", len(df))
    print(status_counts)
    print(status_table.to_string(index=False))


if __name__ == "__main__":
    main()
