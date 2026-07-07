import math
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import qcelemental as qcel
import qcportal


WORKDIR = Path("/home/vlita3/QCMLForge/src/qcml_mcp/full-agentic-workflow/agent_workflow_example")
H2KCALMOL = 627.509474
REFERENCES = {
    "C2C2PD": -20.65,
    "C3A": -16.34,
    "CBH": -11.06,
    "2a": -34.15,
    "S8-2": -30.79,
    "Da2": -20.20,
}


def parse_molecule(path):
    with open(path, "r", errors="ignore") as handle:
        return qcel.models.Molecule.from_data(handle.read())


def level_parts(level):
    method, basis, cp_str = level.split("/")
    return method.lower(), basis.lower(), cp_str.lower()


def normalize_id(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def molecule_key(mol):
    return mol.get_molecular_formula(), len(mol.atomic_numbers)


def record_level(rec):
    spec = rec.specification
    qc_spec = spec.levels[1]
    bsse = spec.bsse_correction[0].value.lower()
    return qc_spec.method.lower(), qc_spec.basis.lower(), bsse


def extract_interaction_energy(rec, level):
    _, _, cp_str = level_parts(level)
    props = rec.properties or {}
    results = props.get("results", {}) if isinstance(props, dict) else {}
    if "cp" in cp_str and "uncp" not in cp_str and "nocp" not in cp_str:
        for key in ("cp_corrected_interaction_energy", "cp_interaction_energy"):
            if key in results:
                return results[key]
            if key in props:
                return props[key]
    for key in ("nocp_corrected_interaction_energy", "nocp_interaction_energy"):
        if key in results:
            return results[key]
        if key in props:
            return props[key]
    if "ret_energy" in props:
        return props["ret_energy"]
    return np.nan


def parse_wall_time(text):
    if not text:
        return 0.0
    total = 0.0
    pattern = re.compile(r"Psi4 wall time for execution:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
    for hours, minutes, seconds in pattern.findall(text):
        total += int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    return total


def child_outputs_and_walltime(rec):
    outputs = []
    wall = 0.0
    for cluster in rec.clusters or []:
        sp = cluster.singlepoint_record
        if sp is None:
            continue
        stdout = sp.stdout or ""
        stderr = sp.stderr or ""
        wall += parse_wall_time(stdout)
        outputs.append(
            {
                "singlepoint_id": sp.id,
                "mc_level": cluster.mc_level,
                "fragments": cluster.fragments,
                "basis": cluster.basis,
                "stdout": stdout,
                "stderr": stderr,
            }
        )
    return outputs, wall if wall > 0 else np.nan


def main():
    client = qcportal.PortalClient("http://localhost:7777", verify=False)
    df = pd.read_pickle(WORKDIR / "run_ies_input.pkl").reset_index(drop=True)
    geom_index = pd.read_csv(WORKDIR / "geom_index.csv")
    mol_by_id = {
        row["id"]: parse_molecule(row["geom_path"])
        for _, row in geom_index.iterrows()
    }
    molecule_key_to_id = {molecule_key(mol): mol_id for mol_id, mol in mol_by_id.items()}

    recs = list(client.query_manybodys(status="complete", include=["**"], limit=None))
    molecule_ids = sorted({r.initial_molecule_id for r in recs if r.initial_molecule_id is not None})
    molecule_map = {}
    if molecule_ids:
        molecules = client.get_molecules(molecule_ids)
        molecule_map = dict(zip(molecule_ids, molecules))

    completed = defaultdict(list)
    for rec in recs:
        mol = molecule_map.get(rec.initial_molecule_id)
        if mol is None:
            continue
        system_id = molecule_key_to_id.get(molecule_key(mol))
        if system_id is None:
            continue
        completed[(system_id, record_level(rec))].append(rec)

    chosen_ids = []
    statuses = []
    energies = []
    walltimes = []
    outputs_col = []
    for _, row in df.iterrows():
        method, basis, cp_str = level_parts(row["Level of Theory"])
        bsse = "cp" if "cp" in cp_str and "uncp" not in cp_str and "nocp" not in cp_str else "nocp"
        matches = completed.get((row["id"], (method, basis, bsse)), [])
        if not matches:
            chosen_ids.append(np.nan)
            statuses.append("missing_complete_duplicate")
            energies.append(np.nan)
            walltimes.append(np.nan)
            outputs_col.append(None)
            continue
        rec = sorted(matches, key=lambda r: r.id)[-1]
        outputs, wall = child_outputs_and_walltime(rec)
        chosen_ids.append([rec.id])
        statuses.append(str(rec.status))
        energies.append(extract_interaction_energy(rec, row["Level of Theory"]))
        walltimes.append(wall)
        outputs_col.append(outputs)

    df["qcfractal id"] = chosen_ids
    df["job status"] = statuses
    df["mb_interaction_energy"] = energies
    df["mb_wall_time"] = walltimes
    df["psi4 output"] = outputs_col
    df["reference_ie"] = df["id"].map(REFERENCES)
    df["mb_interaction_energy_kcalmol"] = df["mb_interaction_energy"] * H2KCALMOL
    df["IE_error_kcalmol"] = df["mb_interaction_energy_kcalmol"] - df["reference_ie"]
    df["actual_abs_percent_error"] = (
        100 * df["IE_error_kcalmol"].abs() / df["reference_ie"].abs()
    )

    df.to_pickle(WORKDIR / "run_ies_queued.pkl", protocol=2)
    df.to_pickle(WORKDIR / "run_ies_results.pkl", protocol=2)
    df.to_pickle(WORKDIR / "full_workflow_results.pkl", protocol=2)

    report_cols = [
        "id",
        "Level of Theory",
        "qcfractal id",
        "job status",
        "mb_interaction_energy_kcalmol",
        "reference_ie",
        "IE_error_kcalmol",
        "actual_abs_percent_error",
        "mb_wall_time",
        "predicted_abs_percent_error",
        "accuracy_bucket",
    ]
    df[report_cols].to_csv(WORKDIR / "full_workflow_results.csv", index=False)

    complete = df["job status"].eq("RecordStatusEnum.complete").sum()
    errored = df["job status"].str.contains("error", case=False, na=False).sum()
    missing = df["job status"].eq("missing_complete_duplicate").sum()
    print("completed", complete, "errored", errored, "missing", missing)
    print(df["job status"].value_counts(dropna=False))
    print("error_stats")
    print(df["IE_error_kcalmol"].agg(["mean", "median", "max", "min"]))
    print(df[report_cols].to_string(index=False))


if __name__ == "__main__":
    main()
