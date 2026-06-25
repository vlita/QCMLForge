from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


RUN_DIR = Path(__file__).resolve().parent
UMAP_CSV_PATH = RUN_DIR / "HB375_BFDBExt_train_apnet2_pair_umap.csv"
OUT_DIR = RUN_DIR / "element_pair_resolved_umaps"
SUMMARY_PATH = RUN_DIR / "HB375_BFDBExt_train_element_pair_umap_summary.json"


def scatter_dataset_overlay(ax, df: pd.DataFrame, title: str, limits: tuple[float, float, float, float]) -> None:
    styles = {
        "BFDBExt train": {"color": "#4c78a8", "alpha": 0.12, "s": 4},
        "HB375": {"color": "#e45756", "alpha": 0.70, "s": 10},
    }
    for dataset, style in styles.items():
        sub = df[df["dataset"] == dataset]
        if sub.empty:
            continue
        ax.scatter(
            sub["umap_1"],
            sub["umap_2"],
            label=f"{dataset} (n={len(sub):,})",
            linewidths=0,
            rasterized=True,
            **style,
        )
    x_min, x_max, y_min, y_max = limits
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.set_xlabel("UMAP 1", fontsize=9)
    ax.set_ylabel("UMAP 2", fontsize=9)
    ax.grid(alpha=0.15, linewidth=0.5)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    df = pd.read_csv(UMAP_CSV_PATH, low_memory=False)
    x_margin = 0.05 * (df["umap_1"].max() - df["umap_1"].min())
    y_margin = 0.05 * (df["umap_2"].max() - df["umap_2"].min())
    limits = (
        float(df["umap_1"].min() - x_margin),
        float(df["umap_1"].max() + x_margin),
        float(df["umap_2"].min() - y_margin),
        float(df["umap_2"].max() + y_margin),
    )

    counts = (
        df.groupby(["pair_label", "dataset"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    for dataset in ["BFDBExt train", "HB375"]:
        if dataset not in counts:
            counts[dataset] = 0
    counts["total"] = counts["BFDBExt train"] + counts["HB375"]
    counts = counts.sort_values(["HB375", "total"], ascending=False)

    plot_pairs = counts[counts["HB375"] > 0]["pair_label"].tolist()
    n_pairs = len(plot_pairs)
    n_cols = 4
    n_rows = int(np.ceil((n_pairs + 1) / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4.2 * n_cols, 3.6 * n_rows))
    axes = np.atleast_1d(axes).ravel()

    scatter_dataset_overlay(axes[0], df, f"All pairs (n={len(df):,})", limits)
    axes[0].legend(frameon=False, fontsize=7, loc="best")

    for ax, pair in zip(axes[1:], plot_pairs):
        sub = df[df["pair_label"] == pair]
        hb_n = int((sub["dataset"] == "HB375").sum())
        bfdb_n = int((sub["dataset"] == "BFDBExt train").sum())
        scatter_dataset_overlay(ax, sub, f"{pair}\nHB375={hb_n:,}, BFDBExt={bfdb_n:,}", limits)

    for ax in axes[n_pairs + 1 :]:
        ax.axis("off")

    fig.suptitle("Element-Pair-Resolved APNet2 Atom-Pair UMAP", fontsize=16, fontweight="bold")
    fig.tight_layout()
    overview_path = OUT_DIR / "element_pair_resolved_umap_overview.png"
    fig.savefig(overview_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    individual_paths = []
    for pair in plot_pairs:
        sub = df[df["pair_label"] == pair]
        fig, ax = plt.subplots(figsize=(7, 6))
        scatter_dataset_overlay(ax, sub, f"{pair} Atom Pairs", limits)
        ax.legend(frameon=False, fontsize=9, loc="best")
        fig.tight_layout()
        safe_pair = pair.replace("-", "_")
        path = OUT_DIR / f"umap_element_pair_{safe_pair}.png"
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        individual_paths.append(str(path))

    summary = {
        "input_umap_csv": str(UMAP_CSV_PATH),
        "output_dir": str(OUT_DIR),
        "overview_plot": str(overview_path),
        "individual_plot_count": len(individual_paths),
        "pair_counts": counts.to_dict(orient="records"),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
