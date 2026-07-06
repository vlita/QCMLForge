from __future__ import annotations

import argparse
import importlib.util
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import qcelemental as qcel


REPO = Path(__file__).resolve().parents[5]
GEOM_DIR = Path(__file__).resolve().parent / "HB375_rest"
RUN_ROOT = Path(__file__).resolve().parent / "runs"
EXAMPLE_MANYBODY = REPO / "src/qcml_mcp/run-IEs/example_manybody.py"
METHODS = ["HF", "PBE-D3", "wB97X-D", "wB97X-V", "MP2", "B3LYP-D3", "B2PLYP-D3"]
BASIS = "aug-cc-pVTZ"


def _load_example_manybody():
    spec = importlib.util.spec_from_file_location("example_manybody", EXAMPLE_MANYBODY)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _parse_comment(comment: str) -> dict[str, str | float | int]:
    fields: dict[str, str | float | int] = {}
    for key, value in re.findall(r"(\w+)=([^\s]+)", comment):
        if key in {"charge", "charge_a", "charge_b"}:
            fields[key] = int(value)
        elif key in {"scaling", "benchmark_Eint"}:
            fields[key] = float(value)
        else:
            fields[key] = value
    return fields


def _parse_selection(selection: str) -> list[int]:
    indices: list[int] = []
    for part in selection.split(","):
        if "-" in part:
            start, stop = part.split("-", 1)
            indices.extend(range(int(start) - 1, int(stop)))
        else:
            indices.append(int(part) - 1)
    return indices


def _read_xyz(path: Path) -> tuple[list[tuple[str, float, float, float]], dict[str, str | float | int]]:
    lines = path.read_text().splitlines()
    n_atoms = int(lines[0].strip())
    metadata = _parse_comment(lines[1])
    atoms = []
    for line in lines[2 : 2 + n_atoms]:
        symbol, x, y, z = line.split()[:4]
        atoms.append((symbol, float(x), float(y), float(z)))
    return atoms, metadata


def _fragment_block(
    atoms: list[tuple[str, float, float, float]],
    indices: list[int],
    charge: int,
) -> str:
    lines = [f"{charge} 1"]
    for idx in indices:
        symbol, x, y, z = atoms[idx]
        lines.append(f"{symbol} {x:.10f} {y:.10f} {z:.10f}")
    return "\n".join(lines)


def parse_hb375_rest_geometry(path: Path) -> dict[str, object]:
    atoms, metadata = _read_xyz(path)
    selection_a = _parse_selection(str(metadata["selection_a"]))
    selection_b = _parse_selection(str(metadata["selection_b"]))
    charge_a = int(metadata.get("charge_a", 0))
    charge_b = int(metadata.get("charge_b", 0))
    geom = "\n--\n".join(
        [
            _fragment_block(atoms, selection_a, charge_a),
            _fragment_block(atoms, selection_b, charge_b),
        ]
    )
    geom = f"{geom}\nunits angstrom\n"
    mol = qcel.models.Molecule.from_data(geom)
    if len(mol.fragments) != 2:
        raise ValueError(f"Expected two fragments for {path}, found {len(mol.fragments)}")
    return {
        "id": path.stem,
        "geom_path": str(path),
        "n_atoms": len(mol.atomic_numbers),
        "qcel_dimer": mol,
        "qcel_monA": mol.get_fragment(0, 1),
        "qcel_monB": mol.get_fragment(1, 0),
        "benchmark_Eint": metadata.get("benchmark_Eint"),
        "benchmark_unit": metadata.get("benchmark_unit"),
        "hb_group": metadata.get("group"),
        "scaling": metadata.get("scaling"),
        "charge": metadata.get("charge"),
        "charge_a": charge_a,
        "charge_b": charge_b,
        "selection_a": metadata.get("selection_a"),
        "selection_b": metadata.get("selection_b"),
    }


def build_submission_dataframe() -> pd.DataFrame:
    rows = [parse_hb375_rest_geometry(path) for path in sorted(GEOM_DIR.glob("*.xyz"))]
    base = pd.DataFrame(rows)
    levels = [f"{method}/{BASIS}/CP" for method in METHODS]
    expanded = base.loc[base.index.repeat(len(levels))].copy()
    expanded["Level of Theory"] = levels * len(base)
    expanded.index = range(len(expanded))
    return expanded


def _normalize_id(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def queue_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    example_manybody = _load_example_manybody()
    queued = example_manybody.queue_manybodys(df.copy())
    queued["submission_time_utc"] = datetime.now(timezone.utc).isoformat()
    queued["submitted_unix_time"] = time.time()
    queued["qcf_tag"] = "free"
    return queued


def write_outputs(df: pd.DataFrame, run_dir: Path, prefix: str) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    df.to_pickle(run_dir / f"{prefix}.pkl", protocol=2)
    df.drop(columns=["qcel_dimer", "qcel_monA", "qcel_monB"], errors="ignore").to_csv(
        run_dir / f"{prefix}.csv", index=False
    )


def write_status(queued: pd.DataFrame, run_dir: Path) -> None:
    example_manybody = _load_example_manybody()
    ids = [_normalize_id(value) for value in queued["qcfractal id"].tolist()]
    records = example_manybody.client.get_manybodys(ids, include=["clusters"])
    rows = []
    for (_, row), rec in zip(queued.iterrows(), records):
        rows.append(
            {
                "id": row["id"],
                "Level of Theory": row["Level of Theory"],
                "benchmark_Eint": row["benchmark_Eint"],
                "benchmark_unit": row["benchmark_unit"],
                "qcfractal id": row["qcfractal id"],
                "normalized_qcfractal_id": _normalize_id(row["qcfractal id"]),
                "job status": str(rec.status) if rec else "missing",
                "n_clusters": len(rec.clusters or []) if rec else 0,
            }
        )
    status = pd.DataFrame(rows)
    status.to_csv(run_dir / "queued_status.csv", index=False)
    status["job status"].value_counts(dropna=False).rename_axis("job status").to_csv(
        run_dir / "queued_status_counts.csv"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-name", default=None)
    args = parser.parse_args()

    run_name = args.run_name or datetime.now().strftime("HB375_rest_free_%Y%m%d_%H%M%S")
    run_dir = RUN_ROOT / run_name
    df = build_submission_dataframe()
    write_outputs(df, run_dir, "run_ies_input")

    summary = {
        "run_dir": str(run_dir),
        "n_geometries": int(df["id"].nunique()),
        "n_rows": int(len(df)),
        "levels": sorted(df["Level of Theory"].unique().tolist()),
        "dry_run": bool(args.dry_run),
    }
    (run_dir / "queue_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    if args.dry_run:
        return

    queued = queue_dataframe(df)
    write_outputs(queued, run_dir, "run_ies_queued")
    write_status(queued, run_dir)
    print(f"queued {len(queued)} manybody records to tag free")
    print(f"saved outputs under {run_dir}")


if __name__ == "__main__":
    main()
