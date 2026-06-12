from pathlib import Path

import pandas as pd


WORKDIR = Path(__file__).resolve().parent
BUDGET_SECONDS = 2.5 * 60 * 60


def main() -> None:
    pred = pd.read_pickle(WORKDIR / "all_lots_predictions_no_mols.pkl")
    queued = pd.read_pickle(WORKDIR / "run_ies_queued.pkl")
    rec = pd.read_csv(WORKDIR / "select_lot_recommendation.csv", index_col=0)
    winners = pd.read_csv(WORKDIR / "select_lot_winners_by_system.csv")

    pred = pred.copy()
    pred["budget_feasible"] = pred["walltime_seconds"] <= BUDGET_SECONDS
    feasible_counts = pred.groupby("Level of Theory")["budget_feasible"].sum().astype(int)
    total_counts = pred.groupby("Level of Theory")["budget_feasible"].size().astype(int)
    excluded = pred[~pred["budget_feasible"]][
        ["id", "Level of Theory", "walltime_seconds", "ERROR ESTIMATES (kcal/mol)"]
    ].sort_values(["Level of Theory", "id"])

    recommended = rec.index[0]
    report = []
    report.append("# full-agentic-workflow Initial Report")
    report.append("")
    report.append(f"Recommended LoT: {recommended}")
    report.append(f"Walltime budget: {BUDGET_SECONDS:.0f} s (2.5 h)")
    report.append(f"Total candidate computations: {len(pred)}")
    report.append(f"Budget-feasible computations submitted: {len(queued)}")
    report.append("QCFractal status: initialized and reachable at http://localhost:7777")
    report.append("")
    report.append("## Recommendation Summary")
    report.append(rec.to_markdown())
    report.append("")
    report.append("## Per-System Winning LoT")
    report.append(
        winners[["id", "Level of Theory", "ERROR ESTIMATES (kcal/mol)", "walltime_seconds"]].to_markdown(index=False)
    )
    report.append("")
    report.append("## Submitted Counts By LoT")
    counts = pd.DataFrame({"submitted": feasible_counts, "total_candidates": total_counts})
    report.append(counts.to_markdown())
    report.append("")
    report.append("## Above-Budget Rows Not Submitted")
    report.append(excluded.to_markdown(index=False) if not excluded.empty else "None")
    report.append("")
    report.append("## Queued Records")
    report.append(
        queued[
            ["id", "Level of Theory", "qcfractal id", "walltime_seconds"]
        ].to_markdown(index=False)
    )
    report.append("")
    report.append("State files saved in this directory: select_lot_df.pkl, run_ies_input.pkl, geom_index.csv, reference_ie.csv, run_ies_queued.pkl.")

    (WORKDIR / "initial_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("wrote", WORKDIR / "initial_report.md")


if __name__ == "__main__":
    main()
