import ast
from pathlib import Path

import pandas as pd
import qcportal


WORKDIR = Path(__file__).resolve().parent


def normalize_id(value):
    if isinstance(value, list):
        return value[0] if value else None
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except Exception:
            return value
        if isinstance(parsed, list):
            return parsed[0] if parsed else None
        return parsed
    return value


def rec_status(record) -> str:
    if record is None:
        return "missing"
    return str(record.status).replace("RecordStatusEnum.", "")


def child_status_counts(record) -> dict[str, int]:
    counts = {}
    if record is None or not getattr(record, "clusters", None):
        return counts
    for cluster in record.clusters:
        sp = getattr(cluster, "singlepoint_record", None)
        if sp is None:
            continue
        status = str(sp.status).replace("RecordStatusEnum.", "")
        counts[status] = counts.get(status, 0) + 1
    return counts


def interaction_energy_present(record) -> bool:
    if record is None or rec_status(record) != "complete":
        return False
    props = record.properties or {}
    if "interaction_energy" in props or "interaction_energies" in props:
        return True
    results = props.get("results", {}) if isinstance(props, dict) else {}
    return any("interaction_energy" in key for key in results)


def main() -> None:
    expected = pd.read_pickle(WORKDIR / "run_ies_queued_all.pkl").copy()
    expected["qcf_id_norm"] = expected["qcfractal id"].map(normalize_id)

    client = qcportal.PortalClient("http://localhost:7777", verify=False)
    records = client.get_manybodys(
        expected["qcf_id_norm"].tolist(), include=["clusters", "**"]
    )

    audit_rows = []
    for (_, row), record in zip(expected.iterrows(), records):
        status = rec_status(record)
        levels = getattr(record, "levels", None) if record is not None else None
        bsse = getattr(record, "bsse_correction", None) if record is not None else None
        audit_rows.append(
            {
                "id": row["id"],
                "expected_lot": row["Level of Theory"],
                "qcf_id": row["qcf_id_norm"],
                "record_exists": record is not None,
                "status": status,
                "child_statuses": child_status_counts(record),
                "completed_ie_present": interaction_energy_present(record),
                "server_levels": str(levels),
                "server_bsse_correction": str(bsse),
            }
        )

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(WORKDIR / "reconnection_audit.csv", index=False)

    summary = {
        "expected_records": len(expected),
        "unique_expected_qcf_ids": expected["qcf_id_norm"].nunique(),
        "records_found": int(audit["record_exists"].sum()),
        "missing_records": int((~audit["record_exists"]).sum()),
        "status_counts": audit["status"].value_counts().to_dict(),
        "completed_without_ie_property": int(
            ((audit["status"] == "complete") & (~audit["completed_ie_present"])).sum()
        ),
    }

    child_totals = {}
    for counts in audit["child_statuses"]:
        for status, count in counts.items():
            child_totals[status] = child_totals.get(status, 0) + count
    summary["child_status_counts"] = child_totals

    lines = [
        "# QCFractal Reconnection Audit",
        "",
        f"Expected queued records: {summary['expected_records']}",
        f"Unique expected QCFractal IDs: {summary['unique_expected_qcf_ids']}",
        f"Records found on server: {summary['records_found']}",
        f"Missing records: {summary['missing_records']}",
        f"Status counts: {summary['status_counts']}",
        f"Child status counts: {summary['child_status_counts']}",
        f"Completed records missing IE property: {summary['completed_without_ie_property']}",
        "",
        "## Missing Records",
        audit[~audit["record_exists"]][["id", "expected_lot", "qcf_id"]].to_markdown(index=False)
        if summary["missing_records"]
        else "None",
        "",
        "## Completed Records",
        audit[audit["status"] == "complete"][
            ["id", "expected_lot", "qcf_id", "completed_ie_present"]
        ].to_markdown(index=False),
        "",
        "## Noncomplete Records",
        audit[audit["status"] != "complete"][
            ["id", "expected_lot", "qcf_id", "status", "child_statuses"]
        ].to_markdown(index=False),
    ]
    (WORKDIR / "reconnection_audit.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    print(summary)
    print("wrote", WORKDIR / "reconnection_audit.csv")
    print("wrote", WORKDIR / "reconnection_audit.md")


if __name__ == "__main__":
    main()
