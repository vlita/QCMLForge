from pathlib import Path

import pandas as pd


WORKDIR = Path("/home/vlita3/QCMLForge/src/qcml_mcp/full-agentic-workflow/agent_workflow_example")


def main():
    df = pd.read_pickle(WORKDIR / "full_workflow_results.pkl")
    completed = df[df["job status"].eq("RecordStatusEnum.complete")].copy()
    completed["walltime_hours"] = completed["mb_wall_time"] / 3600

    bucket_summary = (
        df.groupby(["Level of Theory", "accuracy_bucket"])
        .size()
        .unstack(fill_value=0)
    )
    for col in ["high_accuracy", "medium_accuracy", "low_accuracy", "not_recommended"]:
        if col not in bucket_summary.columns:
            bucket_summary[col] = 0
    bucket_summary["median_predicted_abs_percent_error"] = df.groupby("Level of Theory")[
        "predicted_abs_percent_error"
    ].median()
    bucket_summary = bucket_summary[
        [
            "high_accuracy",
            "medium_accuracy",
            "low_accuracy",
            "not_recommended",
            "median_predicted_abs_percent_error",
        ]
    ].sort_values("median_predicted_abs_percent_error")

    lot_actual = completed.groupby("Level of Theory").agg(
        completed_rows=("id", "count"),
        mean_signed_error=("IE_error_kcalmol", "mean"),
        median_signed_error=("IE_error_kcalmol", "median"),
        mean_abs_error=("IE_error_kcalmol", lambda s: s.abs().mean()),
        median_actual_abs_percent_error=("actual_abs_percent_error", "median"),
        median_walltime_hours=("walltime_hours", "median"),
    )
    lot_actual = lot_actual.sort_values(
        ["median_actual_abs_percent_error", "median_walltime_hours"]
    )

    recommended = completed[completed["accuracy_bucket"].ne("not_recommended")].copy()
    recommended = recommended.sort_values(
        ["predicted_abs_percent_error", "mb_wall_time"]
    )[
        [
            "id",
            "Level of Theory",
            "accuracy_bucket",
            "predicted_abs_percent_error",
            "actual_abs_percent_error",
            "IE_error_kcalmol",
            "walltime_hours",
        ]
    ]

    bucket_summary.to_csv(WORKDIR / "final_bucket_summary.csv")
    lot_actual.to_csv(WORKDIR / "final_lot_actual_summary.csv")
    recommended.to_csv(WORKDIR / "final_recommendations.csv", index=False)

    lines = []
    lines.append("# Full Agentic Workflow Report")
    lines.append("")
    lines.append("Budget: 9000 seconds (2.5 hours) for prediction filtering.")
    lines.append("QCFractal: reachable at http://localhost:7777; completed duplicate records reused.")
    lines.append("Manybody verification: 41 complete, 0 errored, 1 skipped missing complete duplicate.")
    lines.append("")
    lines.append("## Predicted Accuracy Buckets")
    lines.append(bucket_summary.to_markdown())
    lines.append("")
    lines.append("## Actual Error Summary By LoT")
    lines.append(lot_actual.to_markdown())
    lines.append("")
    lines.append("## Recommended Completed Rows")
    lines.append(recommended.to_markdown(index=False))
    lines.append("")
    lines.append("## Overall Completed Error Stats")
    lines.append(completed["IE_error_kcalmol"].agg(["mean", "median", "max", "min"]).to_markdown())
    lines.append("")
    missing = df[df["job status"].ne("RecordStatusEnum.complete")][
        ["id", "Level of Theory", "job status"]
    ]
    lines.append("## Skipped/Missing Rows")
    lines.append(missing.to_markdown(index=False))
    (WORKDIR / "final_report.md").write_text("\n".join(lines) + "\n")

    print("bucket_summary")
    print(bucket_summary)
    print("actual_summary")
    print(lot_actual)
    print("missing")
    print(missing.to_string(index=False))


if __name__ == "__main__":
    main()
