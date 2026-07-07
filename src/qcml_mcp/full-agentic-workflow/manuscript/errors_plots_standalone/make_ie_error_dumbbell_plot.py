"""Generate IE-error dumbbell plots with transparent molecule image underlays."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.offsetbox import (
    AnchoredOffsetbox,
    AnnotationBbox,
    OffsetImage,
    TextArea,
    VPacker,
)
import pandas as pd


SYSTEM_ORDER = ("C2C2PD", "C3A", "CBH", "2a", "S8-2", "Da2")
METHOD_ORDER = (
    "B2PLYP-D3",
    "MP2",
    "wB97X-V",
    "wB97X-D",
    "B3LYP-D3",
    "PBE-D3",
    "HF",
)

PREDICTED_COLOR = "#149708"
TITLE_SIZE = 15
REF_SIZE = 14
X_TICK_SIZE = 10
Y_TICK_SIZE = 14
AXIS_LABEL_SIZE = 14
LEGEND_SIZE = 14
ACTUAL_MARKER_SIZE = 52
PREDICTED_MARKER_SIZE = 52
ZERO_LINE_WIDTH = 1.5
DUMBBELL_LINE_WIDTH = 2.0
GRID_LINE_WIDTH = 1.5
GRID_LINE_COLOR = "0.88"

# Image-underlay controls. OffsetImage preserves each PNG's native aspect ratio.
IMAGE_DIR = Path(__file__).with_name("L14_new")
IMAGE_ALPHA = 1.0 # 0.40
DEFAULT_IMAGE_CENTER = (0.55, 0.50)
DEFAULT_IMAGE_ZOOM = 0.18
IMAGE_PLACEMENT = {
    "C2C2PD": {"center": (0.70, 0.70), "zoom": 0.30},
    "C3A": {"center": (0.67, 0.71), "zoom": 0.19},
    "CBH": {"center": (0.655, 0.70), "zoom": 0.17},
    "2a": {"center": (0.72, 0.66), "zoom": 0.18},
    "S8-2": {"center": (0.72, 0.68), "zoom": 0.20},
    "Da2": {"center": (0.68, 0.66), "zoom": 0.20},
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
        "reference_ie",
        "ACTUAL IE Error",
        "PREDICTED IE Error",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data = df[df["job status"].eq("complete")].copy()
    data["method"] = data["Level of Theory"].str.split("/").str[0]
    data = data[data["id"].isin(SYSTEM_ORDER) & data["method"].isin(METHOD_ORDER)]
    data = data.dropna(subset=["ACTUAL IE Error", "PREDICTED IE Error"])
    data["system_order"] = data["id"].map({s: i for i, s in enumerate(SYSTEM_ORDER)})
    data["method_order"] = data["method"].map({m: i for i, m in enumerate(METHOD_ORDER)})
    return data.sort_values(["system_order", "method_order"])


def _axis_limits(data: pd.DataFrame) -> tuple[float, float]:
    values = pd.concat([data["ACTUAL IE Error"], data["PREDICTED IE Error"]])
    lo = float(values.min())
    hi = float(values.max())
    pad = max(1.0, 0.08 * (hi - lo))
    return lo - pad, hi + pad


def _add_system_image(ax: plt.Axes, system: str) -> None:
    image_path = IMAGE_DIR / f"{system}.png"
    if not image_path.exists():
        return

    image = mpimg.imread(image_path)
    placement = IMAGE_PLACEMENT.get(system, {})
    center = placement.get("center", DEFAULT_IMAGE_CENTER)
    zoom = placement.get("zoom", DEFAULT_IMAGE_ZOOM)

    image_box = OffsetImage(image, zoom=zoom, alpha=IMAGE_ALPHA)
    annotation = AnnotationBbox(
        image_box,
        center,
        xycoords=ax.transAxes,
        frameon=False,
        box_alignment=(0.5, 0.5),
        pad=0.0,
        zorder=6,
    )
    annotation.set_clip_path(ax.patch)
    ax.add_artist(annotation)


def make_plot(data: pd.DataFrame, output_prefix: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(15.0, 9.0), sharex=True)
    axes = axes.ravel()
    x_min, x_max = _axis_limits(data)
    method_to_y = {method: idx for idx, method in enumerate(METHOD_ORDER)}

    for ax, system in zip(axes, SYSTEM_ORDER):
        system_data = data[data["id"].eq(system)]
        reference_ie = float(system_data["reference_ie"].iloc[0])
        ax.axvline(0.0, color=GRID_LINE_COLOR, lw=ZERO_LINE_WIDTH, ls="--", zorder=1)
        _add_system_image(ax, system)

        for _, row in system_data.iterrows():
            method = row["method"]

            if method == "B2PLYP-D3" and system == "C2C2PD":
                continue

            y_pos = method_to_y[method]
            actual = float(row["ACTUAL IE Error"])
            predicted = float(row["PREDICTED IE Error"])
            ax.plot(
                [actual, predicted],
                [y_pos, y_pos],
                color="0.55",
                lw=DUMBBELL_LINE_WIDTH,
                zorder=2,
            )
            ax.scatter(
                actual,
                y_pos,
                s=ACTUAL_MARKER_SIZE,
                marker="o",
                color="black",
                edgecolor="white",
                linewidth=0.5,
                zorder=3,
            )
            ax.scatter(
                predicted,
                y_pos,
                s=PREDICTED_MARKER_SIZE,
                marker="D",
                color=PREDICTED_COLOR,
                edgecolor="white",
                linewidth=0.5,
                zorder=4,
            )

        title_box = VPacker(
            children=[
                TextArea(system, textprops={"weight": "bold", "size": TITLE_SIZE}),
                TextArea(
                    f"ref. {reference_ie:.2f}",
                    textprops={"color": "0.45", "size": REF_SIZE},
                ),
            ],
            align="center",
            pad=0,
            sep=1,
        )
        anchored_title = AnchoredOffsetbox(
            loc="lower center",
            child=title_box,
            pad=0.0,
            frameon=False,
            bbox_to_anchor=(0.5, 1.04),
            bbox_transform=ax.transAxes,
            borderpad=0.0,
        )
        ax.add_artist(anchored_title)
        if system == "C2C2PD":
            ax.set_yticks(range(1, len(METHOD_ORDER)))
            ax.set_yticklabels(METHOD_ORDER[1:])
        else: 
            ax.set_yticks(range(len(METHOD_ORDER)))
            ax.set_yticklabels(METHOD_ORDER)
        ax.invert_yaxis()
        ax.set_xlim(x_min, x_max)
        for tick in ax.get_xticks():
            if x_min <= tick <= x_max and abs(tick) > 1e-9:
                ax.axvline(tick, color=GRID_LINE_COLOR, lw=GRID_LINE_WIDTH, zorder=0.5)
        ax.tick_params(axis="x", labelsize=X_TICK_SIZE)
        ax.tick_params(axis="y", labelsize=Y_TICK_SIZE)
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)

    for ax in axes:
        ax.tick_params(axis="x", labelbottom=True)

    for ax in axes:
        ax.set_xlabel("IE error (kcal mol$^{-1}$)", fontsize=AXIS_LABEL_SIZE)

    actual_handle = plt.Line2D(
        [0],
        [0],
        marker="o",
        linestyle="",
        color="black",
        markeredgecolor="white",
        markersize=7,
        label="Actual IE error",
    )
    predicted_handle = plt.Line2D(
        [0],
        [0],
        marker="D",
        linestyle="",
        color=PREDICTED_COLOR,
        markerfacecolor=PREDICTED_COLOR,
        markeredgecolor="white",
        markersize=7,
        label="Predicted IE error",
    )
    fig.legend(
        handles=[actual_handle, predicted_handle],
        loc="lower center",
        ncol=2,
        frameon=False,
        bbox_to_anchor=(0.5, -0.005),
        fontsize=LEGEND_SIZE,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 0.96), w_pad=3.0, h_pad=3.2)
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
        default=Path(__file__).with_name("ie_error_dumbbell_plot_underlay"),
        help="Output path prefix. The script writes .pdf and .png files.",
    )
    args = parser.parse_args()

    data = _prepare_data(_read_results(args.input))
    make_plot(data, args.output_prefix)
    print(f"Wrote {args.output_prefix.with_suffix('.pdf')}")
    print(f"Wrote {args.output_prefix.with_suffix('.png')}")


if __name__ == "__main__":
    main()
