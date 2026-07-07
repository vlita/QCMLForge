"""Generate actual-vs-predicted interaction-energy error parity plots."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


METHOD_ORDER = (
    "HF",
    "PBE-D3",
    "B3LYP-D3",
    "wB97X-D",
    "wB97X-V",
    "MP2",
    "B2PLYP-D3",
)
SYSTEM_ORDER = ("C2C2PD", "C3A", "CBH", "2a", "S8-2", "Da2")
METHOD_COLORS = {
    "HF": "#0072B2",
    "PBE-D3": "#009E73",
    "B3LYP-D3": "#D55E00",
    "wB97X-D": "#CC79A7",
    "wB97X-V": "#56B4E9",
    "MP2": "#E69F00",
    "B2PLYP-D3": "#6A3D9A",
}
SYSTEM_MARKERS = {
    "C2C2PD": "o",
    "C3A": "s",
    "CBH": "^",
    "2a": "D",
    "S8-2": "P",
    "Da2": "X",
}


def _read_results(path: Path) -> pd.DataFrame:
    if path.suffix == ".pkl":
        return pd.read_pickle(path)
    return pd.read_csv(path)


def _prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    required = {
        "id",
        "Level of Theory",
        "job status",
        "PREDICTED IE Error",
        "ACTUAL IE Error",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data = df[df["job status"].eq("complete")].copy()
    data["method"] = data["Level of Theory"].str.split("/").str[0]
    data = data[data["id"].isin(SYSTEM_ORDER) & data["method"].isin(METHOD_ORDER)]
    data = data.dropna(subset=["PREDICTED IE Error", "ACTUAL IE Error"])
    data["system_order"] = data["id"].map({system: i for i, system in enumerate(SYSTEM_ORDER)})
    data["method_order"] = data["method"].map({method: i for i, method in enumerate(METHOD_ORDER)})
    return data.sort_values(["system_order", "method_order"])


def _axis_limit(data: pd.DataFrame) -> float:
    max_abs = data[["ACTUAL IE Error", "PREDICTED IE Error"]].abs().max().max()
    return float(max(5.0, max_abs * 1.12))


def make_combined_plot(data: pd.DataFrame, output_prefix: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.8, 5.4))
    limit = _axis_limit(data)

    for system in SYSTEM_ORDER:
        system_data = data[data["id"].eq(system)]
        if system_data.empty:
            continue
        for method in METHOD_ORDER:
            rows = system_data[system_data["method"].eq(method)]
            if rows.empty:
                continue
            ax.scatter(
                rows["ACTUAL IE Error"],
                rows["PREDICTED IE Error"],
                s=58,
                marker=SYSTEM_MARKERS[system],
                color=METHOD_COLORS[method],
                edgecolor="white",
                linewidth=0.6,
                zorder=3,
            )

    ax.plot([-limit, limit], [-limit, limit], color="0.25", lw=1.0, ls="--", zorder=1)
    ax.axhline(0, color="0.75", lw=0.8, zorder=0)
    ax.axvline(0, color="0.75", lw=0.8, zorder=0)
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Actual IE error (kcal mol$^{-1}$)")
    ax.set_ylabel("Predicted IE error (kcal mol$^{-1}$)")

    method_handles = [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            color=METHOD_COLORS[method],
            markeredgecolor="white",
            markersize=7,
            label=method,
        )
        for method in METHOD_ORDER
    ]
    system_handles = [
        plt.Line2D(
            [0],
            [0],
            marker=SYSTEM_MARKERS[system],
            linestyle="",
            color="0.25",
            markerfacecolor="0.25",
            markersize=7,
            label=system,
        )
        for system in SYSTEM_ORDER
    ]
    method_legend = ax.legend(
        handles=method_handles,
        title="Method",
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        frameon=False,
    )
    ax.add_artist(method_legend)
    ax.legend(
        handles=system_handles,
        title="System",
        loc="lower left",
        bbox_to_anchor=(1.02, 0.0),
        frameon=False,
    )

    fig.tight_layout()
    fig.savefig(output_prefix.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(output_prefix.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def make_faceted_plot(data: pd.DataFrame, output_prefix: Path) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(7.2, 9.0), sharex=True, sharey=True)
    axes = axes.ravel()
    limit = _axis_limit(data)

    for ax, system in zip(axes, SYSTEM_ORDER):
        system_data = data[data["id"].eq(system)]
        ax.plot([-limit, limit], [-limit, limit], color="0.25", lw=0.9, ls="--", zorder=1)
        ax.axhline(0, color="0.78", lw=0.7, zorder=0)
        ax.axvline(0, color="0.78", lw=0.7, zorder=0)
        for method in METHOD_ORDER:
            rows = system_data[system_data["method"].eq(method)]
            if rows.empty:
                continue
            ax.scatter(
                rows["ACTUAL IE Error"],
                rows["PREDICTED IE Error"],
                s=58,
                marker="o",
                color=METHOD_COLORS[method],
                edgecolor="white",
                linewidth=0.6,
                zorder=3,
            )
        ax.set_title(system, loc="left", fontweight="bold")
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.set_aspect("equal", adjustable="box")

    for ax in axes[-2:]:
        ax.set_xlabel("Actual IE error (kcal mol$^{-1}$)")
    for ax in axes[::2]:
        ax.set_ylabel("Predicted IE error (kcal mol$^{-1}$)")

    handles = [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            color=METHOD_COLORS[method],
            markeredgecolor="white",
            markersize=7,
            label=method,
        )
        for method in METHOD_ORDER
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=4,
        frameon=False,
        bbox_to_anchor=(0.5, -0.01),
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(output_prefix.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(output_prefix.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).with_name("full_workflow_results.csv"),
        help="Input workflow results CSV or PKL.",
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path(__file__).with_name("ie_error_parity_plot"),
        help="Output path prefix. The script writes .pdf and .png files.",
    )
    parser.add_argument(
        "--facet",
        action="store_true",
        help="Write a 2x3 faceted-by-system plot instead of one combined plot.",
    )
    args = parser.parse_args()

    data = _prepare_data(_read_results(args.input))
    if args.facet:
        make_faceted_plot(data, args.output_prefix)
    else:
        make_combined_plot(data, args.output_prefix)

    print(f"Wrote {args.output_prefix.with_suffix('.pdf')}")
    print(f"Wrote {args.output_prefix.with_suffix('.png')}")


if __name__ == "__main__":
    main()
