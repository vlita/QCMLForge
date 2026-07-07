from pathlib import Path

import pandas as pd


WORKDIR = Path("/home/vlita3/QCMLForge/src/qcml_mcp/full-agentic-workflow/agent_workflow_example")
INPUT = WORKDIR / "full_workflow_results.pkl"
OUTPUT = WORKDIR / "lao2024_estimator_comparison_table.tex"


METHOD_ORDER = [
    "HF",
    "PBE-D3",
    "wB97X-D",
    "wB97X-V",
    "MP2",
    "B3LYP-D3",
    "B2PLYP-D3",
]
BUCKET_ORDER = ["high", "medium", "low", "not rec."]


def assign_bucket(percent_error):
    if percent_error < 2:
        return "high"
    if percent_error < 5:
        return "medium"
    if percent_error < 10:
        return "low"
    return "not rec."


def bucket_counts(values):
    normalized = (
        values.astype(str)
        .str.replace("_accuracy", "", regex=False)
        .str.replace("not_recommended", "not rec.", regex=False)
    )
    counts = normalized.value_counts()
    return "/".join(str(int(counts.get(bucket, 0))) for bucket in BUCKET_ORDER)


def format_row(method, group):
    pred_counts = bucket_counts(group["accuracy_bucket"])
    actual_counts = bucket_counts(group["actual_accuracy_bucket"])
    return (
        f"        {method} & "
        f"{group['predicted_abs_percent_error'].mean():.1f} & "
        f"{group['actual_abs_percent_error'].mean():.1f} & "
        f"{pred_counts} & "
        f"{actual_counts} \\\\"
    )


def main():
    df = pd.read_pickle(INPUT)
    df = df[df["job status"].eq("RecordStatusEnum.complete")].copy()
    df["Method"] = df["Level of Theory"].str.split("/").str[0]
    df["actual_accuracy_bucket"] = df["actual_abs_percent_error"].map(assign_bucket)

    rows = []
    for method in METHOD_ORDER:
        group = df[df["Method"].eq(method)]
        if group.empty:
            continue
        rows.append(format_row(method, group))

    table = r"""\begin{table*}
    \centering
    \caption{Per-method performance of error estimator models on the chosen subset of L14. Predicted percent errors are calculated from $\Delta$APNet2 predictions relative to the CCSD(T)/CBS reference interaction energies (in kcal mol$^{-1}$). Accuracy counts are reported as high/medium/low/not recommended using the $<2\%$, $2$--$5\%$, $5$--$10\%$, and $\geq10\%$ thresholds, respectively. All computations utilized the counterpoise correction.}
    \label{tab:lao2024_estimator_comparison}
    \begin{tabular*}{\textwidth}{@{\extracolsep{\fill}} lcccc}
        \hline
        Method & \begin{tabular}{c}Mean Pred. \\ \% Error\end{tabular} & \begin{tabular}{c}Mean Actual \\ \% Error\end{tabular} & \begin{tabular}{c}Predicted Accuracy \\ Counts (H/M/L/NR)\end{tabular} & \begin{tabular}{c}Actual Accuracy \\ Counts (H/M/L/NR)\end{tabular} \\
        \hline
"""
    table += "\n".join(rows)
    table += r"""
        \hline
    \end{tabular*}
\end{table*}
"""
    OUTPUT.write_text(table)
    print(f"Wrote {OUTPUT}")
    print(table)


if __name__ == "__main__":
    main()
