from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import qcportal


WORKDIR = Path("/home/vlita3/QCMLForge/src/qcml_mcp/full-agentic-workflow/agent_workflow_example")


def main():
    client = qcportal.PortalClient("http://localhost:7777", verify=False)
    df = pd.read_pickle(WORKDIR / "run_ies_input.pkl").reset_index(drop=True)
    rows = []
    for lot in sorted(df["Level of Theory"].dropna().unique()):
        method, basis, _ = lot.split("/")
        recs = list(
            client.query_manybodys(
                program="qcmanybody",
                qc_program="psi4",
                qc_method=method,
                qc_basis=basis,
                include=["**"],
            )
        )
        counts = Counter(str(r.status) for r in recs)
        rows.append(
            {
                "Level of Theory": lot,
                "records_found": len(recs),
                **dict(counts),
            }
        )
        examples = defaultdict(list)
        for rec in recs:
            examples[str(rec.status)].append(rec.id)
        print("\n", lot)
        print("counts", dict(counts))
        for status, ids in sorted(examples.items()):
            print(status, ids[:30])

    pd.DataFrame(rows).fillna(0).to_csv(WORKDIR / "phase3_existing_record_counts.csv", index=False)


if __name__ == "__main__":
    main()
