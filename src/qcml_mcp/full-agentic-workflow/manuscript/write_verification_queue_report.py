from pathlib import Path

import pandas as pd


WORKDIR = Path(__file__).resolve().parent


def main() -> None:
    queued_excluded = pd.read_pickle(WORKDIR / "run_ies_queued_excluded.pkl")
    queued_all = pd.read_pickle(WORKDIR / "run_ies_queued_all.pkl")

    lines = [
        "# Verification Queue Report",
        "",
        f"Above-budget verification jobs submitted: {len(queued_excluded)}",
        f"Total queued jobs including original budget-feasible jobs: {len(queued_all)}",
        "",
        "## Newly Queued Above-Budget Jobs",
        queued_excluded[
            ["id", "Level of Theory", "qcfractal id", "walltime_seconds"]
        ].to_markdown(index=False),
        "",
        "## Combined Queue Counts By LoT",
        queued_all.groupby("Level of Theory").size().rename("queued").to_frame().to_markdown(),
        "",
        "Use run_ies_queued_all.pkl for final all-computation status checks, retrieval, and post-processing.",
    ]
    (WORKDIR / "verification_queue_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("wrote", WORKDIR / "verification_queue_report.md")


if __name__ == "__main__":
    main()
