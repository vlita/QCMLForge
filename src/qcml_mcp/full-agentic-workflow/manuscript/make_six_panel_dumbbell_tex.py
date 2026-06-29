"""Generate a LaTeX six-panel dumbbell figure for large-dimer IE results."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_SYSTEM_ORDER = ("C2C2PD", "C3A", "CBH", "2a", "S8-2", "Da2")
DEFAULT_METHOD_ORDER = (
    "HF",
    "PBE-D3",
    "B3LYP-D3",
    "wB97X-D",
    "wB97X-V",
    "MP2",
    "B2PLYP-D3",
)
# METHOD_COLORS = (
#     "9986A5",  # HF
#     "79402E",  # PBE-D3
#     "CCBA72",  # B3LYP-D3
#     "EAD3BF",  # wB97X-D
#     "D9D0D3",  # wB97X-V
#     "8D8680",  # MP2
#     "B6854D",  # B2PLYP-D3
# )
METHOD_COLORS = (
 "F1BB7B", "FD6467", "5B1A18", "D67236", "E6A0C4", "C6CDF7", "7294D4"
)
LEGEND_METHODS = (
    ("B2PLYP-D3", "B2PLYP-D3"),
    ("MP2", "MP2"),
    ("wB97X-V", "*B97X-V"),
    ("wB97X-D", "*B97X-D"),
    ("B3LYP-D3", "B3LYP-D3"),
    ("PBE-D3", "PBE-D3"),
    ("HF", "HF"),
)
IMAGE_WIDTHS = {
    "C2C2PD": "3.00cm",
    "C3A": "3.00cm",
    "CBH": "3.00cm",
    "2a": "2.70cm",
    "S8-2": "2.50cm",
    "Da2": "2.70cm",
}
IMAGE_Y_OFFSETS = {
    "C2C2PD": "-0.10cm",
    "C3A": "-0.55cm",
    "CBH": "-0.45cm",
    "2a": "-0.10cm",
    "S8-2": "-0.15cm",
    "Da2": "-0.10cm",
}
IMAGE_X_OFFSETS = {
    "C2C2PD": "-0.05cm",
    "C3A": "0.05cm",
    "CBH": "0.05cm",
    "2a": "0.20cm",
    "S8-2": "0.15cm",
    "Da2": "0.25cm",
}


def _tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "*": r"$\omega$",
    }
    return "".join(replacements.get(char, char) for char in str(text))


def _read_results(path: Path) -> pd.DataFrame:
    if path.suffix == ".pkl":
        return pd.read_pickle(path)
    return pd.read_csv(path)


def _prepare_data(
    df: pd.DataFrame,
    system_order: tuple[str, ...],
    method_order: tuple[str, ...],
) -> pd.DataFrame:
    required = {
        "id",
        "Level of Theory",
        "job status",
        "mb_ie_kcalmol",
        "reference_ie",
        "PREDICTED IE Error",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data = df[df["job status"].eq("complete")].copy()
    data["method"] = data["Level of Theory"].str.split("/").str[0]
    data = data[data["id"].isin(system_order) & data["method"].isin(method_order)]
    data = data.dropna(subset=["mb_ie_kcalmol", "reference_ie", "PREDICTED IE Error"])
    data["corrected_ie"] = data["mb_ie_kcalmol"] - data["PREDICTED IE Error"]
    data["corrected_error"] = data["corrected_ie"] - data["reference_ie"]
    data["system_order"] = data["id"].map({s: i for i, s in enumerate(system_order)})
    data["method_order"] = data["method"].map({m: i for i, m in enumerate(method_order)})
    return data.sort_values(["system_order", "method_order"])


def _panel_tex(system: str, panel_label: str, rows: pd.DataFrame) -> str:
    ref = float(rows["reference_ie"].iloc[0])
    error_ticks = (-4.0, -2.0, 0.0, 2.0, 4.0)
    tick_positions = [ref + error for error in error_ticks]
    x_margin = 0.8
    xmin = min(rows["corrected_ie"].min(), *tick_positions) - x_margin
    xmax = max(rows["corrected_ie"].max(), *tick_positions) + x_margin
    y_max = len(rows) + 0.55
    xtick = ",".join(f"{tick:.3f}" for tick in tick_positions)
    xticklabels = r"{-4},{-2},{0},{+2},{+4}"
    lines: list[str] = []

    for y_pos, row in enumerate(rows.itertuples(index=False), start=1):
        method_color = f"methodColor{int(row.method_order)}"
        corrected = float(row.corrected_ie)
        lines.append(
            rf"\draw[dumbbellLine] (axis cs:{ref:.3f},{y_pos}) -- "
            rf"(axis cs:{corrected:.3f},{y_pos});"
        )
        lines.append(rf"\node[refDot] at (axis cs:{ref:.3f},{y_pos}) {{}};")
        lines.append(
            rf"\node[predDot, fill={method_color}] at "
            rf"(axis cs:{corrected:.3f},{y_pos}) {{}};"
        )

    drawing = "\n".join(lines)
    system_tex = _tex_escape(system)
    image_path = f"L14_new/{system}.png"
    image_width = IMAGE_WIDTHS.get(system, "3.00cm")
    image_y = IMAGE_Y_OFFSETS.get(system, "-0.55cm")
    image_x = IMAGE_X_OFFSETS.get(system, "0.05cm")

    return rf"""\resizebox{{0.46\textwidth}}{{!}}{{%
\begin{{tikzpicture}}
\node[anchor=north west, inner sep=0pt] (img) at ({image_x},{image_y}) {{%
  \IfFileExists{{{image_path}}}{{%
    \includegraphics[width={image_width}]{{{image_path}}}%
  }}{{%
    \begin{{tikzpicture}}[x=1cm,y=1cm]
      \draw[placeholderBox] (0,0) rectangle (1.75,1.35);
      \node[placeholderText] at (0.875,0.76) {{molecule}};
      \node[placeholderText] at (0.875,0.50) {{{system_tex}}};
    \end{{tikzpicture}}%
  }}%
}};
\begin{{axis}}[
  at={{(2.95cm,-0.02cm)}},
  anchor=north west,
  width=5.75cm,
  height=3.95cm,
  xmin={xmin:.3f}, xmax={xmax:.3f},
  ymin=0.35, ymax={y_max:.3f},
  axis x line*=bottom,
  axis y line=none,
  xlabel={{}},
  xtick={{{xtick}}},
  xticklabels={{{xticklabels}}},
  xticklabel style={{font=\scriptsize\sffamily, rotate=0, anchor=north}},
  xlabel style={{font=\tiny\sffamily, yshift=1pt}},
  tick align=outside,
  ytick=\empty,
  clip=false,
  grid=major,
  major grid style={{gray!18}},
]
\draw[refLine] (axis cs:{ref:.3f},0.45) -- (axis cs:{ref:.3f},{y_max - 0.10:.3f});
\node[refLabel] at (axis cs:{ref:.3f},{y_max:.3f}) {{ref. {ref:.2f}}};
{drawing}
\end{{axis}}
\node[panelTitle, anchor=north west] at (0.0cm,0.28cm) {{{system_tex}}};
\end{{tikzpicture}}
}}"""


def _document_tex(data: pd.DataFrame, system_order: tuple[str, ...]) -> str:
    panels = []
    for idx, system in enumerate(system_order):
        rows = data[data["id"].eq(system)]
        if rows.empty:
            continue
        panels.append(_panel_tex(system, chr(ord("a") + idx), rows))

    rows = [" & ".join(panels[i : i + 2]) for i in range(0, len(panels), 2)]
    joined_panels = " \\\\[1.0em]\n".join(rows)
    color_defs = "\n".join(
        rf"\definecolor{{methodColor{idx}}}{{HTML}}{{{color}}}"
        for idx, color in enumerate(METHOD_COLORS)
    )
    method_to_color_idx = {method: idx for idx, method in enumerate(DEFAULT_METHOD_ORDER)}
    legend_cells = []
    for method, label in LEGEND_METHODS:
        color_idx = method_to_color_idx[method]
        legend_cells.append(
            rf"\makebox[0.090\textwidth][c]{{\tikz[baseline=-1.0ex]{{\node[circle, draw=white, "
            rf"fill=methodColor{color_idx}, minimum size=8.5pt, inner sep=0pt] {{}};}}"
            rf"\hspace{{0.20em}}{{\large\sffamily {_tex_escape(label)}}}}}"
        )
    legend_tex = " & ".join(legend_cells)

    return rf"""\documentclass[10pt]{{article}}
\usepackage[paperwidth=12in,paperheight=14in,margin=0.35in]{{geometry}}
\usepackage{{graphicx}}
\usepackage{{array}}
\usepackage{{subcaption}}
\usepackage{{tikz}}
\usepackage{{pgfplots}}
\usetikzlibrary{{calc}}
\pgfplotsset{{compat=1.18}}

\pagestyle{{empty}}
\definecolor{{refColor}}{{HTML}}{{222222}}
\definecolor{{predColor}}{{HTML}}{{1F77B4}}
\definecolor{{lineColor}}{{HTML}}{{7A7A7A}}
{color_defs}
\tikzset{{
  dumbbellLine/.style={{line width=0.75pt, lineColor}},
  refLine/.style={{line width=0.55pt, dashed, refColor}},
  refDot/.style={{circle, draw=white, fill=refColor, minimum size=3.8pt, inner sep=0pt}},
  predDot/.style={{circle, draw=white, fill=predColor, minimum size=4.5pt, inner sep=0pt}},
  methodLabel/.style={{anchor=west, font=\scriptsize\sffamily, text=black}},
  valueLabel/.style={{font=\scriptsize\sffamily, text=black}},
  refLabel/.style={{anchor=south, font=\scriptsize\sffamily, text=refColor, fill=white, inner sep=1pt}},
  panelTitle/.style={{font=\bfseries\small\sffamily}},
  placeholderBox/.style={{draw=gray!55, fill=gray!7, rounded corners=2pt, line width=0.45pt}},
  placeholderText/.style={{font=\scriptsize\sffamily, text=gray!65}},
}}

\begin{{document}}
\centering
\vspace{{0.45em}}
\begin{{tabular}}{{@{{}}cc@{{}}}}
{joined_panels}
\end{{tabular}}
\vspace{{3em}}

\begin{{tabular}}{{@{{}}ccccccc@{{}}}}
{legend_tex}
\end{{tabular}}
\end{{document}}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).with_name("full_workflow_results.csv"),
        help="Input workflow results CSV or PKL.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("six_panel_dumbbell_figure.tex"),
        help="Output LaTeX file.",
    )
    args = parser.parse_args()

    df = _read_results(args.input)
    data = _prepare_data(df, DEFAULT_SYSTEM_ORDER, DEFAULT_METHOD_ORDER)
    tex = _document_tex(data, DEFAULT_SYSTEM_ORDER)
    args.output.write_text(tex, encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
