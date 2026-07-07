from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd


ROOT = Path(__file__).resolve().parent
SYSTEM_GRID = [
    ["S8-2", "Da2"],
    ["CBH", "C3A"],
    ["C2C2PD", "2a"],
]
METHODS = ["HF", "PBE-D3", "B3LYP-D3", "wB97X-D", "wB97X-V", "MP2", "B2PLYP-D3"]
COLORS = {
    "HF": "#4c78a8",
    "PBE-D3": "#f58518",
    "B3LYP-D3": "#54a24b",
    "wB97X-D": "#e45756",
    "wB97X-V": "#72b7b2",
    "MP2": "#b279a2",
    "B2PLYP-D3": "#ff9da6",
}


def read_ordered_values(system: str, filename: str) -> pd.DataFrame:
    df = pd.read_csv(ROOT / system / filename)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["value"]).reset_index(drop=True)


def fmt_value(value: float) -> str:
    text = f"{value:.2f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def draw_value_ordering_pair(
    ax,
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    left_title: str,
    right_title: str,
    left_label: str,
    right_label: str,
    x_left: float,
    x_right: float,
    y_top: float = 0.72,
    y_step: float = 0.074,
) -> None:
    common_methods = [
        method
        for method in METHODS
        if method in set(left_df["method"]) and method in set(right_df["method"])
    ]
    left_df = left_df[left_df["method"].isin(common_methods)].reset_index(drop=True)
    right_df = right_df[right_df["method"].isin(common_methods)].reset_index(drop=True)
    left_methods = left_df["method"].tolist()
    right_methods = right_df["method"].tolist()
    left_values = dict(zip(left_df["method"], left_df["value"]))
    right_values = dict(zip(right_df["method"], right_df["value"]))
    left_y = {method: y_top - idx * y_step for idx, method in enumerate(left_methods)}
    right_y = {method: y_top - idx * y_step for idx, method in enumerate(right_methods)}
    box_width = 0.120
    box_height = y_step

    ax.text(x_left, y_top + 0.13, left_title, ha="center", va="bottom", fontsize=8)
    ax.text(x_right, y_top + 0.13, right_title, ha="center", va="bottom", fontsize=8)
    ax.text(x_left, y_top - len(left_methods) * y_step - 0.035, left_label, ha="center", va="top", fontsize=8)
    ax.text(x_right, y_top - len(right_methods) * y_step - 0.035, right_label, ha="center", va="top", fontsize=8)

    for method in common_methods:
        ax.plot(
            [x_left + box_width / 2, x_right - box_width / 2],
            [left_y[method], right_y[method]],
            color="#7a7a7a",
            linewidth=1.0,
            alpha=0.85,
            zorder=0,
        )

    for method in left_methods:
        ax.add_patch(
            Rectangle(
                (x_left - box_width / 2, left_y[method] - box_height / 2),
                box_width,
                box_height,
                facecolor=COLORS[method],
                edgecolor="#222222",
                linewidth=0.65,
                zorder=2,
            )
        )
        ax.text(
            x_left,
            left_y[method],
            fmt_value(left_values[method]),
            ha="center",
            va="center",
            fontsize=9.4,
            color="white",
            zorder=3,
        )

    for method in right_methods:
        ax.add_patch(
            Rectangle(
                (x_right - box_width / 2, right_y[method] - box_height / 2),
                box_width,
                box_height,
                facecolor=COLORS[method],
                edgecolor="#222222",
                linewidth=0.65,
                zorder=2,
            )
        )
        ax.text(
            x_right,
            right_y[method],
            fmt_value(right_values[method]),
            ha="center",
            va="center",
            fontsize=9.4,
            color="white",
            zorder=3,
        )


def draw_system(ax, system: str) -> None:
    pred_error = read_ordered_values(system, "predicted_error_estimates.csv")
    actual_error = read_ordered_values(system, "actual_ie_errors.csv")
    pred_time = read_ordered_values(system, "estimated_cpu_times_log10_s.csv")
    actual_time = read_ordered_values(system, "manybody_wall_time_log10_s.csv")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(
        0.50,
        1.04,
        system,
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=13,
        fontweight="bold",
        clip_on=False,
    )

    draw_value_ordering_pair(
        ax,
        pred_error,
        actual_error,
        "IE Error",
        "IE Error",
        "Pred.",
        "Actual",
        x_left=0.24,
        x_right=0.41,
    )
    draw_value_ordering_pair(
        ax,
        pred_time,
        actual_time,
        "CPU Time",
        "Wall Time",
        "Pred.",
        "Actual",
        x_left=0.59,
        x_right=0.76,
    )


def add_method_legend(fig) -> None:
    handles = [
        plt.Line2D(
            [0],
            [0],
            marker="s",
            linestyle="None",
            markerfacecolor=COLORS[method],
            markeredgecolor="#222222",
            markersize=8,
            label=method,
        )
        for method in METHODS
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=len(METHODS),
        frameon=False,
        bbox_to_anchor=(0.5, 0.015),
        fontsize=9,
        handlelength=2.6,
        columnspacing=1.4,
    )


def main() -> None:
    plt.rcParams.update(
        {
            "text.usetex": False,
            "font.family": "DejaVu Sans",
            "mathtext.fontset": "dejavusans",
        }
    )
    fig, axes = plt.subplots(3, 2, figsize=(8.9, 7.6), constrained_layout=False)
    for row_idx, row in enumerate(SYSTEM_GRID):
        for col_idx, system in enumerate(row):
            draw_system(axes[row_idx, col_idx], system)

    add_method_legend(fig)
    fig.subplots_adjust(left=0.015, right=0.995, top=0.985, bottom=0.11, wspace=-0.12, hspace=0.18)
    fig.savefig(ROOT / "system_ordering_value_slope_plot.png", dpi=300, bbox_inches="tight")
    fig.savefig(ROOT / "system_ordering_value_slope_plot.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {ROOT / 'system_ordering_value_slope_plot.png'}")
    print(f"wrote {ROOT / 'system_ordering_value_slope_plot.pdf'}")


if __name__ == "__main__":
    main()
