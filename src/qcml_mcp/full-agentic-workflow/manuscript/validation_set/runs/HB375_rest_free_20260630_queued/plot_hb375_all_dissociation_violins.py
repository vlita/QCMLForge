from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
INPUT_CSV = ROOT / "HB375_all_dissociation_violin_plot_input.csv"
OUTPUT_BASENAME = ROOT / "HB375_all_dissociation_dapnet2_error_cdsg_no_latex"
STATS_CSV = ROOT / "HB375_all_dissociation_violin_plot_error_statistics_cdsg_no_latex.csv"

METHODS = [
    "HF",
    "PBE-D3",
    "B3LYP-D3",
    "wB97X-D",
    "wB97X-V",
    "MP2",
    "B2PLYP-D3",
]


def plot_violin_errors_per_df(df: pd.DataFrame, output_filename: str) -> None:
    from cdsg_plot import error_statistics
    from matplotlib.axes import Axes
    from matplotlib.text import Text

    original_text = Axes.text
    original_set_text = Text.set_text

    def no_latex_text(self, x, y, s, *args, **kwargs):
        if isinstance(s, str):
            s = strip_latex_wrappers(s)
        return original_text(self, x, y, s, *args, **kwargs)

    def no_latex_set_text(self, s):
        if isinstance(s, str):
            s = strip_latex_wrappers(s)
        return original_set_text(self, s)

    df_labels_and_columns = {}
    for method in METHODS:
        level = f"{method}/aug-cc-pVTZ/CP"
        short_level = f"{method}/aTZ/CP"
        df_labels_and_columns[f"{short_level} Error"] = f"{level} Error"
        df_labels_and_columns[f"dAPNet2+{short_level} Error"] = f"dAPNet2+{level} Error"

    dfs = [
        {
            "df": df,
            "label": "",
            "ylim": [[-10.0, 10.0]],
        }
    ]

    Axes.text = no_latex_text
    Text.set_text = no_latex_set_text
    try:
        error_statistics.violin_plot_table_multi_SAPT_components(
            dfs,
            df_labels_and_columns_total=df_labels_and_columns,
            output_filename=output_filename,
            figure_size=(12, 4),
            ylabel="IE Error vs. CCSD(T)/CBS (kcal/mol)",
            grid_widths=[1],
            grid_heights=[0.2, 1],
            usetex=False,
            rcParams={
                "text.usetex": False,
                "font.family": "sans-serif",
                "font.sans-serif": "DejaVu Sans",
                "mathtext.fontset": "dejavusans",
            },
        )
    finally:
        Axes.text = original_text
        Text.set_text = original_set_text


def strip_latex_wrappers(text: str) -> str:
    replacements = {
        r"\noindent": "",
        r"\textit": "",
        r"\textbf": "",
        r"\textrm": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("{", "").replace("}", "")
    return text


def write_error_statistics(df: pd.DataFrame) -> None:
    rows = []
    for method in METHODS:
        level = f"{method}/aug-cc-pVTZ/CP"
        for column in (f"{level} Error", f"dAPNet2+{level} Error"):
            values = df[column].dropna().to_numpy(dtype=float)
            rows.append(
                {
                    "label": column,
                    "column": column,
                    "MAE": float(np.mean(np.abs(values))),
                    "RMSE": float(np.sqrt(np.mean(values**2))),
                    "MaxE": float(np.max(values)),
                    "MinE": float(np.min(values)),
                }
            )
    pd.DataFrame(rows).to_csv(STATS_CSV, index=False)


def main() -> None:
    df = pd.read_csv(INPUT_CSV)
    write_error_statistics(df)
    plot_violin_errors_per_df(df, output_filename=f"{OUTPUT_BASENAME}.png")
    plot_violin_errors_per_df(df, output_filename=f"{OUTPUT_BASENAME}.pdf")
    print(f"read {INPUT_CSV}")
    print(f"wrote {OUTPUT_BASENAME}_violin.png")
    print(f"wrote {OUTPUT_BASENAME}_violin.pdf")
    print(f"wrote {STATS_CSV}")


if __name__ == "__main__":
    main()
