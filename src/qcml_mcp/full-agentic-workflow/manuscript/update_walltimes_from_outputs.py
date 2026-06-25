"""Populate mb_wall_time from Psi4 stdout files for the Lao workflow."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import qcportal


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "psi4_outputs"
WALLTIME_RE = re.compile(
    r"Psi4 wall time for execution:\s*(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)"
)
MBID_RE = re.compile(r"__mbid_(\d+)__spid_(\d+)\.stdout\.txt$")


def normalize_id(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def seconds_from_match(match: re.Match[str]) -> float:
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = float(match.group(3))
    return hours * 3600 + minutes * 60 + seconds


def parse_stdout_walltime(path: Path) -> tuple[int, int, float] | None:
    name_match = MBID_RE.search(path.name)
    if not name_match:
        return None
    text = path.read_text(errors="ignore")
    time_match = WALLTIME_RE.search(text)
    if not time_match:
        return None
    return int(name_match.group(1)), int(name_match.group(2)), seconds_from_match(time_match)


def safe_prefix(level: str, system_id: str, mbid: int, spid: int) -> str:
    return f"{level.replace('/', '_')}__{system_id}__mbid_{mbid}__spid_{spid}"


def write_missing_outputs(df: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    client = qcportal.PortalClient("http://localhost:7777", verify=False)
    ids = [normalize_id(v) for v in df["qcfractal id"].tolist()]
    ids = [v for v in ids if v is not None]
    records = client.get_manybodys(ids, include=["clusters", "**"])
    rows_by_mbid = {
        normalize_id(row["qcfractal id"]): row for _, row in df.iterrows()
    }
    manifest_entries = set()
    manifest_path = OUTPUT_DIR / "MANIFEST.txt"
    if manifest_path.exists():
        manifest_entries.update(
            line.strip() for line in manifest_path.read_text().splitlines() if line.strip()
        )

    for rec in records:
        if rec is None:
            continue
        row = rows_by_mbid.get(rec.id)
        if row is None:
            continue
        for cluster in rec.clusters or []:
            sp = cluster.singlepoint_record
            if sp is None:
                continue
            prefix = safe_prefix(row["Level of Theory"], row["id"], rec.id, sp.id)
            for attr in ("stdout", "stderr"):
                text = getattr(sp, attr, None)
                if not text:
                    continue
                path = OUTPUT_DIR / f"{prefix}.{attr}.txt"
                if not path.exists():
                    path.write_text(text)
                manifest_entries.add(str(path.relative_to(ROOT)))

    manifest_path.write_text("\n".join(sorted(manifest_entries)) + "\n")


def aggregate_walltimes() -> pd.DataFrame:
    rows = []
    for path in OUTPUT_DIR.glob("*.stdout.txt"):
        parsed = parse_stdout_walltime(path)
        if parsed is None:
            continue
        mbid, spid, seconds = parsed
        rows.append(
            {
                "qcfractal_id": mbid,
                "singlepoint_id": spid,
                "stdout_path": str(path.relative_to(ROOT)),
                "psi4_wall_time_seconds": seconds,
            }
        )
    parsed = pd.DataFrame(rows)
    parsed.to_csv(ROOT / "parsed_psi4_walltimes.csv", index=False)
    if parsed.empty:
        return pd.DataFrame(columns=["qcfractal_id", "mb_wall_time"])
    summed = (
        parsed.groupby("qcfractal_id", as_index=False)["psi4_wall_time_seconds"]
        .sum()
        .rename(columns={"psi4_wall_time_seconds": "mb_wall_time"})
    )
    summed.to_csv(ROOT / "summed_manybody_walltimes.csv", index=False)
    return summed


def main() -> None:
    results_path = ROOT / "full_workflow_results.pkl"
    df = pd.read_pickle(results_path).copy()
    write_missing_outputs(df)
    walltimes = aggregate_walltimes()
    walltime_map = dict(zip(walltimes["qcfractal_id"], walltimes["mb_wall_time"]))
    df["mb_wall_time"] = df["qcfractal id"].map(
        lambda value: walltime_map.get(normalize_id(value), np.nan)
    )
    df.to_pickle(results_path, protocol=2)
    df.to_csv(ROOT / "full_workflow_results.csv", index=False)

    merged_path = ROOT / "run_ies_results_merged.pkl"
    if merged_path.exists():
        merged = pd.read_pickle(merged_path).copy()
        merged["mb_wall_time"] = merged["qcfractal id"].map(
            lambda value: walltime_map.get(normalize_id(value), np.nan)
        )
        merged.to_pickle(merged_path, protocol=2)
        merged.to_csv(ROOT / "run_ies_results_merged.csv", index=False)

    print(f"parsed stdout files: {len(pd.read_csv(ROOT / 'parsed_psi4_walltimes.csv'))}")
    print(f"rows with mb_wall_time: {int(df['mb_wall_time'].notna().sum())}/{len(df)}")


if __name__ == "__main__":
    main()
