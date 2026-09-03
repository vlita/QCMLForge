"""Generate an OpenCode-style visual of the full agentic QC workflow.

The figure is intentionally schematic: it depicts what a user sees and does
rather than documenting the implementation internals. Edit the constants in
the first section to change the example prompt, methods, or color palette.

Examples
--------
Run with the environment used to create the checked-in figure::

    /home/yung/miniconda3/envs/ai4qc/bin/python make_agentic_workflow_ui.py

Choose a different output stem or raster resolution::

    python make_agentic_workflow_ui.py --output my_workflow --dpi 300
"""

from __future__ import annotations

import argparse
import re
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnnotationBbox, HPacker, TextArea
from matplotlib.patches import Arc, Ellipse, FancyArrowPatch, FancyBboxPatch, PathPatch, Polygon, Rectangle
from matplotlib.path import Path as MplPath
from matplotlib.transforms import Affine2D


# ---------------------------------------------------------------------------
# Easily editable content and visual theme
# ---------------------------------------------------------------------------

EXAMPLE_PROMPT = "Run full-agentic-workflow on the 350 dimer geometries in @dimer_dataset/. Use the CCSD(T)/CBS references from @SI.pdf and a 2.5 hour walltime budget. Consider all levels of theory in the SI, and show me the accuracy options before submitting calculations."

METHODS = (
    ("PBE-D3 / aTZ", "high", "1.4%", "38 min"),
    ("wB97X-V / aTZ", "high", "1.8%", "1.6 h"),
    ("B3LYP-D3 / aTZ", "medium", "3.2%", "52 min"),
    ("MP2 / aTZ", "low", "7.1%", "2.1 h"),
    ("HF / aTZ", "not rec.", "18%", "12 min"),
    ("B2PLYP-D3 / aTZ", "medium", "4.4%", "2.6 h"),
)

COLORS = {
    "paper": "#F4F1EA",
    "paper_dark": "#E8E1D5",
    "ink": "#17222D",
    "muted": "#66717A",
    "line": "#AAB2B5",
    "terminal": "#111417",
    "terminal_2": "#1B2025",
    "terminal_text": "#F5F3ED",
    "orange": "#F28B54",
    "blue": "#4CA8D8",
    "green": "#48A985",
    "yellow": "#E5B94C",
    "red": "#D96C68",
    "violet": "#8B7EC8",
    "white": "#FFFFFF",
}

FONT_SANS = "DejaVu Sans"
FONT_MONO = "DejaVu Sans Mono"
SOURCE_FIGURE_WIDTH = 10.5
SOURCE_FIGURE_HEIGHT = 13.5
FIGURE_WIDTH = 13.5
FIGURE_HEIGHT = 12.8
_DRAW_SCALE_X = 1.0
_DRAW_SCALE_Y = 1.0
_FONT_SCALE = 1.0


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def rounded_box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    facecolor: str,
    edgecolor: str = "none",
    linewidth: float = 1.0,
    radius: float = 0.015,
    zorder: int = 1,
):
    """Add a rounded rectangle in normalized figure coordinates."""
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.004,rounding_size={radius}",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=linewidth,
        transform=ax.transAxes,
        clip_on=False,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def circle(
    ax,
    x: float,
    y: float,
    radius: float,
    *,
    facecolor: str,
    edgecolor: str = "none",
    linewidth: float = 1.0,
    zorder: int = 5,
):
    """Draw a physical circle despite the portrait axes aspect ratio."""
    patch = Ellipse(
        (x, y),
        width=2 * radius,
        height=(
            2
            * radius
            * FIGURE_WIDTH
            / FIGURE_HEIGHT
            * _DRAW_SCALE_X
            / _DRAW_SCALE_Y
        ),
        transform=ax.transAxes,
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=linewidth,
        clip_on=False,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def text(
    ax,
    x: float,
    y: float,
    value: str,
    *,
    size: float = 10,
    color: str | None = None,
    weight: str = "normal",
    family: str = FONT_SANS,
    ha: str = "left",
    va: str = "center",
    zorder: int = 5,
    linespacing: float = 1.25,
    rotation: float = 0,
):
    """Add consistently styled text in normalized figure coordinates."""
    return ax.text(
        x,
        y,
        value,
        transform=ax.transAxes,
        fontsize=size * _FONT_SCALE,
        color=color or COLORS["ink"],
        fontweight=weight,
        fontfamily=family,
        horizontalalignment=ha,
        verticalalignment=va,
        zorder=zorder,
        linespacing=linespacing,
        rotation=rotation,
    )


def arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str | None = None,
    width: float = 1.7,
    connectionstyle: str = "arc3",
    dashed: bool = False,
    zorder: int = 0,
):
    """Draw a directional connector."""
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=12,
        linewidth=width,
        linestyle="--" if dashed else "-",
        color=color or COLORS["line"],
        connectionstyle=connectionstyle,
        transform=ax.transAxes,
        clip_on=False,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def pill(
    ax,
    x: float,
    y: float,
    label: str,
    *,
    fill: str,
    color: str = "white",
    width: float | None = None,
    height: float = 0.022,
    size: float = 7.5,
    edgecolor: str = "none",
):
    """Draw a compact label pill and return its width."""
    if width is None:
        width = 0.014 + 0.0062 * len(label)
    rounded_box(
        ax,
        x,
        y - height / 2,
        width,
        height,
        facecolor=fill,
        edgecolor=edgecolor,
        linewidth=0.8,
        radius=height / 2,
        zorder=4,
    )
    text(ax, x + width / 2, y, label, size=size, color=color, weight="bold", ha="center")
    return width


def attachment_badge(
    ax,
    x: float,
    y: float,
    kind: str,
    label: str,
    *,
    accent: str,
    height: float = 0.018,
):
    """Draw an OpenCode-style attachment type and path badge."""
    kind_width = 0.013 + 0.0062 * len(kind)
    label_width = 0.014 + 0.0062 * len(label)
    ax.add_patch(
        Rectangle(
            (x, y - height / 2),
            kind_width,
            height,
            transform=ax.transAxes,
            facecolor=accent,
            edgecolor="none",
            zorder=4,
        )
    )
    ax.add_patch(
        Rectangle(
            (x + kind_width, y - height / 2),
            label_width,
            height,
            transform=ax.transAxes,
            facecolor="#292D31",
            edgecolor="none",
            zorder=4,
        )
    )
    text(ax, x + kind_width / 2, y, kind, size=7.5, color=COLORS["ink"], family=FONT_MONO, ha="center")
    text(ax, x + kind_width + 0.007, y, label, size=7.5, color="#B8BEC3", family=FONT_MONO)
    return kind_width + label_width


def terminal_frame(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    context: str = "GPT-5.5",
    title_size: float = 7.8,
):
    """Draw a simplified OpenCode terminal window."""
    rounded_box(
        ax,
        x,
        y,
        w,
        h,
        facecolor=COLORS["terminal"],
        edgecolor="#30363C",
        linewidth=1.1,
        radius=0.012,
        zorder=2,
    )
    bar_h = 0.026
    rounded_box(
        ax,
        x + 0.002,
        y + h - bar_h - 0.002,
        w - 0.004,
        bar_h,
        facecolor=COLORS["terminal_2"],
        radius=0.009,
        zorder=3,
    )
    for i, color in enumerate((COLORS["red"], COLORS["yellow"], COLORS["green"])):
        circle(
            ax,
            x + 0.018 + i * 0.016,
            y + h - bar_h / 2 - 0.003,
            0.004,
            facecolor=color,
            zorder=5,
        )
    render_title_size = title_size * _FONT_SCALE
    title = HPacker(
        children=[
            TextArea("opencode", textprops={"fontsize": render_title_size, "color": "#A9B0B5", "fontfamily": FONT_MONO}),
            TextArea(f"/  {context}  ·", textprops={"fontsize": render_title_size, "color": "#A9B0B5", "fontfamily": FONT_MONO}),
            TextArea("BUILD", textprops={"fontsize": render_title_size, "color": COLORS["blue"], "fontfamily": FONT_MONO, "fontweight": "bold"}),
        ],
        align="center",
        pad=0,
        sep=8 * _FONT_SCALE,
    )
    ax.add_artist(
        AnnotationBbox(
            title,
            (x + 0.068, y + h - bar_h / 2 - 0.003),
            xycoords=ax.transAxes,
            box_alignment=(0, 0.5),
            frameon=False,
            pad=0,
            zorder=5,
        )
    )


def prompt_line(
    ax,
    x: float,
    y: float,
    value: str,
    *,
    width_chars: int = 78,
    font_size: float = 9.5,
    marker_size: float = 10,
    min_box_width: float = 0,
    blank_lines: int = 1,
):
    """Render a boxed, wrapped user prompt and return its text inset."""
    words = value.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > width_chars:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    if not lines:
        lines = [""] * blank_lines
    render_font_size = font_size * _FONT_SCALE
    line_step = render_font_size * 1.35 / (FIGURE_HEIGHT * 72)
    first_line_y = y + (len(lines) - 1) * line_step / 2
    line_positions = [first_line_y - i * line_step for i in range(len(lines))]
    marker_y = (line_positions[0] + line_positions[-1]) / 2
    text_x = x + 0.026

    char_width = render_font_size * 0.60 / (FIGURE_WIDTH * 72)
    box_padding_x = 0.010
    box_padding_y = line_step * 0.55
    content_width = max(len(line) for line in lines) * char_width + 2 * box_padding_x
    rounded_box(
        ax,
        text_x - box_padding_x,
        line_positions[-1] - box_padding_y,
        max(content_width, min_box_width),
        line_positions[0] - line_positions[-1] + 2 * box_padding_y,
        facecolor="#242A2F",
        edgecolor="#353D44",
        linewidth=0.7,
        radius=0.005,
        zorder=3,
    )

    text(ax, x, marker_y, ">", size=marker_size, color=COLORS["orange"], weight="bold", family=FONT_MONO)
    for line, line_y in zip(lines, line_positions):
        if not line:
            continue
        segments = re.split(r"(@dimer_dataset/|@SI\.pdf)", line)
        line_box = HPacker(
            children=[
                TextArea(
                    segment,
                    textprops={
                        "fontsize": render_font_size,
                        "color": "#F0B44D" if segment in {"@dimer_dataset/", "@SI.pdf"} else COLORS["terminal_text"],
                        "fontfamily": FONT_MONO,
                    },
                )
                for segment in segments
                if segment
            ],
            align="center",
            pad=0,
            sep=0,
        )
        ax.add_artist(
            AnnotationBbox(
                line_box,
                (text_x, line_y),
                xycoords=ax.transAxes,
                box_alignment=(0, 0.5),
                frameon=False,
                pad=0,
                zorder=5,
            )
        )
    return text_x


def stage_number(ax, x: float, y: float, number: str, color: str):
    """Draw a numbered stage marker."""
    circle(
        ax,
        x,
        y,
        0.014,
        facecolor=color,
        edgecolor=COLORS["paper"],
        linewidth=2,
        zorder=8,
    )
    text(ax, x, y, number, size=8, color="white", weight="bold", ha="center", zorder=9)


def file_icon(ax, x: float, y: float, color: str, label: str):
    """Draw a small file artifact."""
    w, h = 0.045, 0.049
    rounded_box(
        ax,
        x,
        y,
        w,
        h,
        facecolor=COLORS["white"],
        edgecolor=color,
        linewidth=1.2,
        radius=0.004,
        zorder=3,
    )
    fold = Polygon(
        [[x + w - 0.013, y + h], [x + w, y + h - 0.013], [x + w - 0.013, y + h - 0.013]],
        transform=ax.transAxes,
        facecolor=color,
        edgecolor="none",
        zorder=4,
    )
    ax.add_patch(fold)
    text(ax, x + w / 2, y - 0.010, label, size=6.4, color=COLORS["muted"], ha="center", va="top")


# ---------------------------------------------------------------------------
# Figure sections
# ---------------------------------------------------------------------------

def draw_initial_prompt(ax):
    w, h = 0.80, 0.120
    x, y = (1 - w) / 2, 0.875
    terminal_frame(ax, x, y, w, h)
    prompt_marker_x = x + 0.025
    prompt_line(
        ax,
        prompt_marker_x,
        y + 0.057,
        EXAMPLE_PROMPT,
        width_chars=92,
        min_box_width=0.700,
    )
    badge_x = prompt_marker_x + 0.018
    dir_width = attachment_badge(ax, badge_x, y + 0.016, "dir", "./dimer_dataset/", accent="#5EA7F5")
    attachment_badge(ax, badge_x + dir_width + 0.015, y + 0.016, "pdf", "./SI.pdf", accent=COLORS["red"])


def draw_inputs_and_search(ax):
    x, y, w, h = 0.06, 0.690, 0.88, 0.125
    rounded_box(ax, x, y, w, h, facecolor=COLORS["white"], edgecolor="#D5CEC1", radius=0.012)
    # text(ax, x + 0.025, y + h - 0.026, "IE Error and Timing Models used to  ", size=9.5, weight="bold")

    # Input stack: visual shorthand for arbitrary system count and LoT search.
    geom_dy = -0.008
    for i in range(3):
        rounded_box(
            ax,
            x + 0.025 + i * 0.007,
            y + geom_dy + 0.038 + i * 0.007,
            0.112,
            0.052,
            facecolor="#EEF6F9",
            edgecolor=COLORS["blue"],
            linewidth=0.8,
            radius=0.006,
            zorder=2 + i,
        )
    # Water dimer: two bent O-H-H molecules joined by a hydrogen bond.
    water_a = ((0.050+0.005, 0.060+0.01+0.008), (0.069+0.005+0.006, 0.075+0.01+0.008-0.006), (0.068+0.005-0.006, 0.043+0.01+0.008-0.003))
    water_b = ((0.112, 0.068+0.01), (0.130, 0.083+0.01), (0.130, 0.051+0.01))
    for oxygen, hydrogen_1, hydrogen_2 in (water_a, water_b):
        ax.plot(
            [x + hydrogen_1[0], x + oxygen[0], x + hydrogen_2[0]],
            [y + geom_dy + hydrogen_1[1], y + geom_dy + oxygen[1], y + geom_dy + hydrogen_2[1]],
            color=COLORS["line"],
            lw=1.5,
            transform=ax.transAxes,
            zorder=6,
        )
        circle(ax, x + oxygen[0], y + geom_dy + oxygen[1], 0.0075, facecolor=COLORS["red"], edgecolor="black", linewidth=0.8, zorder=7)
        for hydrogen in (hydrogen_1, hydrogen_2):
            circle(ax, x + hydrogen[0], y + geom_dy + hydrogen[1], 0.0048, facecolor=COLORS["white"], edgecolor="black", linewidth=0.7, zorder=7)
    ax.plot(
        [x + water_a[1][0], x + water_b[0][0]],
        [y + geom_dy + water_a[1][1], y + geom_dy + water_b[0][1]],
        color=COLORS["blue"],
        lw=1.2,
        ls=(0, (2, 2)),
        transform=ax.transAxes,
        zorder=5,
    )
    text(ax, x + 0.081, y + 0.016, "Geometries", size=7.5, color=COLORS["muted"], weight="bold", ha="center")

    # Geometry and user-selected quantum-chemistry settings form the inputs.
    labels = (("HF", COLORS["yellow"]), ("DFT", COLORS["green"]), ("MP2", COLORS["violet"]), ("aDZ", COLORS["blue"]), ("TZ", COLORS["orange"]), ("unCP/CP", COLORS["ink"]))
    for i, (label, color) in enumerate(labels):
        col, row = i % 3, i // 3
        pill(ax, x + 0.195 + col * 0.066, y + 0.082 - row * 0.035, label, fill=color, width=0.054, height=0.023, size=7.4)
    text(ax, x + 0.288, y + 0.020, "Methods, bases, BSSE correction", size=7.3, color=COLORS["muted"], weight="bold", ha="center")

    # Compact neural-network cartoon connecting inputs to model predictions.
    network_layers = (
        (x + 0.414, (y + 0.046, y + 0.064, y + 0.082)),
        (x + 0.450, (y + 0.041, y + 0.057, y + 0.073, y + 0.089)),
        (x + 0.486, (y + 0.052, y + 0.078)),
    )
    ax.add_patch(
        Polygon(
            [
                (x + 0.408, y + 0.054),
                (x + 0.460, y + 0.054),
                (x + 0.460, y + 0.041),
                (x + 0.501, y + 0.065),
                (x + 0.460, y + 0.089),
                (x + 0.460, y + 0.076),
                (x + 0.408, y + 0.076),
            ],
            closed=True,
            transform=ax.transAxes,
            facecolor=COLORS["muted"],
            edgecolor="none",
            alpha=0.18,
            zorder=2,
        )
    )
    for (left_x, left_ys), (right_x, right_ys) in zip(network_layers, network_layers[1:]):
        for left_y in left_ys:
            for right_y in right_ys:
                ax.plot(
                    [left_x, right_x],
                    [left_y, right_y],
                    color="#B9C4CA",
                    lw=0.55,
                    alpha=0.75,
                    transform=ax.transAxes,
                    zorder=3,
                )
    layer_colors = (COLORS["blue"], COLORS["violet"], COLORS["green"])
    for (layer_x, layer_ys), layer_color in zip(network_layers, layer_colors):
        for layer_y in layer_ys:
            circle(ax, layer_x, layer_y, 0.0038, facecolor=layer_color, edgecolor="white", linewidth=0.7, zorder=5)

    # Mini accuracy vs walltime map; budget is a literal filter line.
    px, py, pw, ph = x + 0.535, y + 0.022, 0.190, 0.079
    ax.plot([px, px, px + pw], [py + ph, py, py], color=COLORS["ink"], lw=0.8, transform=ax.transAxes, zorder=3)
    budget_x = px + 0.147
    ax.add_patch(
        Rectangle(
            (budget_x, py),
            px + pw - budget_x,
            ph,
            transform=ax.transAxes,
            facecolor=COLORS["orange"],
            edgecolor=COLORS["orange"],
            linewidth=0,
            hatch="///",
            alpha=0.22,
            zorder=2,
        )
    )
    ax.plot([budget_x, budget_x], [py, py + ph], color=COLORS["orange"], lw=1.2, ls="--", transform=ax.transAxes, zorder=3)
    text(ax, budget_x, py + ph + 0.008, "2.5 h", size=7.2, color=COLORS["orange"], weight="bold", ha="center")
    points = (
        (0.024, 0.067, COLORS["red"]),
        (0.055, 0.042, COLORS["yellow"]),
        (0.087, 0.047, COLORS["orange"]),
        (0.112, 0.034, COLORS["yellow"]),
        (0.132, 0.038, COLORS["yellow"]),
        (0.153, 0.021, COLORS["green"]),
        (0.177, 0.014, COLORS["green"]),
    )
    for dx, dy, color in points:
        circle(ax, px + dx, py + dy, 0.006, facecolor=color, edgecolor="white", linewidth=0.8, zorder=5)
    text(ax, px + pw / 2, py - 0.012, "pred. Wall Time", size=7.2, color=COLORS["muted"], weight="bold", ha="center")
    text(ax, px - 0.018, py + ph / 2, "pred. % Error", size=7.2, color=COLORS["muted"], weight="bold", ha="center", rotation=90)

    bucket_data = (
        ("< 2%", "HIGH", COLORS["green"]),
        ("2–5%", "MED", COLORS["yellow"]),
        ("5–10%", "LOW", COLORS["orange"]),
        ("≥ 10%", "—", COLORS["red"]),
    )
    for i, (threshold, label, color) in enumerate(bucket_data):
        by = y + 0.093 - i * 0.024
        bucket_x = x + 0.757
        bucket_h = 0.014
        rounded_box(ax, bucket_x, by, 0.088, bucket_h, facecolor=color, radius=0.004, zorder=3)
        text(ax, bucket_x + 0.010, by + bucket_h / 2, threshold, size=6.2, color="white", weight="bold")
        text(ax, bucket_x + 0.078, by + bucket_h / 2, label, size=6.2, color="white", weight="bold", ha="right")


def draw_choice_terminal(ax):
    w, h = 0.74, 0.150
    x, y = (1 - w) / 2, 0.496
    terminal_frame(ax, x, y, w, h)
    content_x = x + 0.025
    text(ax, content_x, y + h - 0.044, "◆  Predictions are ready for your review, which calculations should we submit?", size=9.5, color=COLORS["terminal_text"], family=FONT_MONO)
    # text(ax, x + 0.025, y + h - 0.056, "   choose any combination", size=6.8, color="#89949C", family=FONT_MONO)

    row_x = content_x
    row_y = y + 0.073
    card_w = 0.215
    card_h = 0.018
    row_gap = 0.031
    bucket_colors = {"high": COLORS["green"], "medium": COLORS["yellow"], "low": COLORS["orange"], "not rec.": COLORS["red"]}
    for i, (method, bucket, error, runtime) in enumerate(METHODS):
        col = i % 3
        row = i // 3
        bx = row_x + col * 0.235
        by = row_y - row * row_gap
        rounded_box(
            ax,
            bx,
            by,
            card_w,
            card_h,
            facecolor="#181D21",
            edgecolor=bucket_colors[bucket],
            linewidth=1.2,
            radius=0.004,
            zorder=4,
        )
        if method.startswith("B2PLYP-D3"):
            ax.add_patch(
                FancyBboxPatch(
                    (bx, by),
                    card_w,
                    card_h,
                    boxstyle="round,pad=0.004,rounding_size=0.004",
                    transform=ax.transAxes,
                    facecolor=COLORS["orange"],
                    edgecolor=COLORS["orange"],
                    linewidth=0,
                    hatch="///",
                    alpha=0.12,
                    zorder=4,
                )
            )
        card_center_y = by + card_h / 2
        text(ax, bx + 0.012, card_center_y, "○", size=7.8, color=bucket_colors[bucket], weight="bold", family=FONT_MONO)
        text(ax, bx + 0.034, card_center_y, method, size=7.2, color=COLORS["terminal_text"], family=FONT_MONO)
        text(ax, bx + 0.157, card_center_y, error, size=6.8, color=bucket_colors[bucket], family=FONT_MONO, ha="right")
        text(ax, bx + 0.201, card_center_y, runtime, size=6.5, color="#9DA6AC", family=FONT_MONO, ha="right")

    prompt_line(
        ax,
        content_x,
        y + 0.016,
        "Let's run PBE-D3, B3LYP-D3, and MP2 on all systems.",
        width_chars=78,
        font_size=9.5,
        marker_size=10,
        min_box_width=0.670,
    )
    # text(ax, x + 0.025, y + 0.025, "agent waits", size=6.5, color=COLORS["green"], weight="bold", family=FONT_MONO)
    # text(ax, x + 0.120, y + 0.025, "nothing is queued yet", size=6.5, color="#8F999F", family=FONT_MONO)


def draw_orchestration(ax):
    x, y, w, h = 0.06, 0.306, 0.88, 0.146
    rounded_box(ax, x, y, w, h, facecolor="#E8EEF0", edgecolor="#CAD3D5", radius=0.012)

    # QCFractal server cloud.
    cloud_fill = "#DDEEF6"
    cloud_dy = 0.008
    cloud_vertices = [
        (x + 0.045, y + 0.044),
        (x + 0.154, y + 0.044),
        (x + 0.168, y + 0.044), (x + 0.176, y + 0.050), (x + 0.176, y + 0.059),
        (x + 0.176, y + 0.065), (x + 0.171, y + 0.071), (x + 0.162, y + 0.074),
        (x + 0.163, y + 0.082), (x + 0.152, y + 0.088), (x + 0.138, y + 0.088),
        (x + 0.133, y + 0.098), (x + 0.115, y + 0.103), (x + 0.101, y + 0.095),
        (x + 0.092, y + 0.105), (x + 0.070, y + 0.103), (x + 0.062, y + 0.092),
        (x + 0.046, y + 0.094), (x + 0.034, y + 0.086), (x + 0.036, y + 0.077),
        (x + 0.024, y + 0.074), (x + 0.020, y + 0.067), (x + 0.025, y + 0.059),
        (x + 0.025, y + 0.050), (x + 0.032, y + 0.044), (x + 0.045, y + 0.044),
        (x + 0.045, y + 0.044),
    ]
    cloud_codes = [
        MplPath.MOVETO,
        MplPath.LINETO,
        *([MplPath.CURVE4] * 24),
        MplPath.CLOSEPOLY,
    ]
    ax.add_patch(
        PathPatch(
            MplPath(cloud_vertices, cloud_codes),
            transform=Affine2D().translate(0, cloud_dy) + ax.transAxes,
            facecolor=cloud_fill,
            edgecolor=COLORS["blue"],
            linewidth=1.0,
            zorder=3,
        )
    )
    server_command = (
        "client = qc.PortalClient(\n"
        "   \"http://192.0.2.55:8999\",\n"
        "   verify=True)\n"
    )
    text(ax, x + 0.040, y + cloud_dy + 0.060, server_command, size=5.8, color="#246F94", family=FONT_MONO, linespacing=1.12, zorder=6)
    text(ax, x + 0.100, y + cloud_dy + 0.024, "Agent connects to\nQCFractal server", size=7.2, color="#246F94", weight="bold", ha="center")

    # The server branches to either an existing database record or fresh compute.
    arrow(ax, (x + 0.231, y + 0.101), (x + 0.177, y + cloud_dy + 0.071), color=COLORS["green"], width=1.4, connectionstyle="arc3,rad=0.13", zorder=2)
    arrow(ax, (x + 0.177, y + cloud_dy + 0.064), (x + 0.231, y + 0.048), color=COLORS["blue"], width=1.4, connectionstyle="arc3,rad=0.13", zorder=2)

    reuse_x, reuse_y = x + 0.238, y + 0.080
    queue_x, queue_y = x + 0.238, y + 0.025
    branch_w, branch_h = 0.175, 0.041
    rounded_box(ax, reuse_x, reuse_y, branch_w, branch_h, facecolor="#DCEFE7", edgecolor=COLORS["green"], linewidth=1.0, radius=0.007, zorder=3)
    rounded_box(ax, queue_x, queue_y, branch_w, branch_h, facecolor="#DDEEF6", edgecolor=COLORS["blue"], linewidth=1.0, radius=0.007, zorder=3)
    or_x = reuse_x + branch_w / 2
    or_y = y + 0.0745
    ax.add_patch(
        Ellipse(
            (or_x, or_y),
            0.044,
            0.029,
            transform=ax.transAxes,
            facecolor="#E8EEF0",
            edgecolor="none",
            zorder=5,
        )
    )
    ax.add_patch(Arc((or_x, or_y), 0.044, 0.029, theta1=0, theta2=180, transform=ax.transAxes, color=COLORS["green"], linewidth=1.0, zorder=6))
    ax.add_patch(Arc((or_x, or_y), 0.044, 0.029, theta1=180, theta2=360, transform=ax.transAxes, color=COLORS["blue"], linewidth=1.0, zorder=6))
    # rounded_box(ax, or_x - 0.017, or_y - 0.0085, 0.034, 0.017, facecolor=COLORS["violet"], radius=0.0085, zorder=7)
    text(ax, or_x, or_y, "OR", size=7.2, color="#246F94", weight="bold", ha="center", zorder=8)

    # Database cylinder icon.
    db_x, db_y = reuse_x + 0.027, reuse_y + branch_h / 2
    ax.plot([db_x - 0.013, db_x - 0.013], [db_y - 0.011, db_y + 0.011], color="#277A5D", lw=1.0, transform=ax.transAxes, zorder=5)
    ax.plot([db_x + 0.013, db_x + 0.013], [db_y - 0.011, db_y + 0.011], color="#277A5D", lw=1.0, transform=ax.transAxes, zorder=5)
    for disk_y in (db_y + 0.011, db_y + 0.0035, db_y - 0.0035, db_y - 0.011):
        ax.add_patch(Ellipse((db_x, disk_y), 0.026, 0.007, transform=ax.transAxes, facecolor="#F7FBF9", edgecolor="#277A5D", linewidth=1.0, zorder=5))
    text(ax, reuse_x + 0.102, db_y, "retrieve matching\ncalculation results", size=6.7, color="#277A5D", weight="bold", ha="center", linespacing=1.05)

    # Compute-rack icon.
    rack_x, rack_y = queue_x + 0.012, queue_y + 0.007
    for i in range(3):
        slot_y = rack_y + i * 0.009
        rounded_box(ax, rack_x, slot_y, 0.033, 0.006, facecolor="#F7FAFC", edgecolor="#2B789F", linewidth=0.8, radius=0.0015, zorder=4)
        circle(ax, rack_x + 0.006, slot_y + 0.003, 0.0017, facecolor=COLORS["blue"], zorder=5)
        ax.plot([rack_x + 0.012, rack_x + 0.027], [slot_y + 0.003, slot_y + 0.003], color="#2B789F", lw=0.8, transform=ax.transAxes, zorder=5)
    text(ax, queue_x + 0.105, queue_y + branch_h / 2, "submit new jobs to\nexisting resources", size=6.7, color="#2B789F", weight="bold", ha="center", linespacing=1.05)

    # Both paths feed the visible subset of a longer manybody queue.
    jobs_x = x + 0.505
    job_fill = "#D4D9DC"
    arrow(ax, (x + 0.420, queue_y + branch_h / 2), (jobs_x - 0.010, y + 0.065), color=COLORS["line"], width=1.2, connectionstyle="arc3,rad=-0.10", zorder=2)
    rounded_box(ax, jobs_x, y + 0.118, 0.140, 0.018, facecolor=job_fill, radius=0.004, zorder=3)
    for dot_x in (jobs_x + 0.058, jobs_x + 0.070, jobs_x + 0.082):
        circle(ax, dot_x, y + 0.127, 0.0022, facecolor=COLORS["muted"], zorder=4)
    for i in range(3):
        job_y = y + 0.091 - i * 0.027
        rounded_box(ax, jobs_x, job_y, 0.140, 0.018, facecolor=job_fill, radius=0.004, zorder=3)
        text(ax, jobs_x + 0.070, job_y + 0.009, ("JOB #481", "JOB #482", "JOB #483")[i], size=8.2, color=COLORS["ink"], weight="bold", family=FONT_MONO, ha="center")
    rounded_box(ax, jobs_x, y + 0.010, 0.140, 0.018, facecolor=job_fill, radius=0.004, zorder=3)
    for dot_x in (jobs_x + 0.058, jobs_x + 0.070, jobs_x + 0.082):
        circle(ax, dot_x, y + 0.019, 0.0022, facecolor=COLORS["muted"], zorder=4)

    # Queued state is persisted as one unlabeled stack of artifacts.
    arrow(ax, (jobs_x + 0.148, y + 0.072), (x + 0.724, y + 0.072), color=COLORS["violet"], width=1.3, zorder=2)
    paper_colors = (COLORS["blue"], COLORS["green"], COLORS["violet"])
    for i, paper_color in enumerate(paper_colors):
        paper_x = x + 0.738 + i * 0.017
        paper_y = y + 0.039 + i * 0.014
        rounded_box(ax, paper_x, paper_y, 0.060, 0.064, facecolor=COLORS["white"], edgecolor=paper_color, linewidth=1.1, radius=0.004, zorder=3 + i)
        ax.add_patch(
            Polygon(
                [[paper_x + 0.046, paper_y + 0.064], [paper_x + 0.060, paper_y + 0.050], [paper_x + 0.046, paper_y + 0.050]],
                transform=ax.transAxes,
                facecolor=paper_color,
                edgecolor="none",
                zorder=4 + i,
            )
        )
    text(ax, x + 0.785, y + 0.017, "Checkpoint files created", size=7.2, color="#246F94", weight="bold", ha="center")


def draw_sessions(ax):
    x, y, w, h = 0.06, 0.123, 0.88, 0.140
    # text(ax, x, y + h + 0.016, "RETURN WHEN IT SUITS YOU", size=9.5, weight="bold")
    # text(ax, x + 0.220, y + h + 0.016, "state persists between conversations", size=7.2, color=COLORS["muted"])

    card_w = 0.266
    gap = 0.041
    sessions = (
        ("First Session", "All jobs submitted and running, checkpoint files saved.", "", COLORS["yellow"]),
        ("LATER", "25 jobs complete, 13 errored, and 1012 still running.", "Check job status.", COLORS["blue"]),
        ("WHEN COMPLETE", "All jobs complete.", "Provide a detailed summary of results.", COLORS["green"]),
    )
    for i, (tab, agent_message, user_message, color) in enumerate(sessions):
        sx = x + i * (card_w + gap)
        terminal_frame(ax, sx, y, card_w, h, title_size=7.8)
        if i == 0:
            wrapped_agent = (
                "All jobs submitted and\n"
                "running, checkpoint\n"
                "files saved."
            )
        else:
            wrapped_agent = textwrap.fill(
                agent_message,
                width=20,
            )
        if i == 0:
            text(ax, sx + 0.018, y + 0.081, "◆", size=10.0, color=COLORS["terminal_text"], family=FONT_MONO)
            text(ax, sx + 0.040, y + 0.081, wrapped_agent, size=10.0, color=COLORS["terminal_text"], family=FONT_MONO, linespacing=1.05)
            text(ax, sx + 0.040, y + 0.052, "+ checkpoint.csv", size=8.5, color=COLORS["green"], weight="bold", family=FONT_MONO)
            text(ax, sx + 0.040, y + 0.041, "+ reccomendations.md", size=8.5, color=COLORS["green"], weight="bold", family=FONT_MONO)
            prompt_line(
                ax,
                sx + 0.018,
                y + 0.014,
                user_message,
                width_chars=18,
                font_size=10.5,
                marker_size=11,
                min_box_width=0.205,
                blank_lines=1,
            )
        elif i == 1:
            prompt_line(
                ax,
                sx + 0.018,
                y + 0.091,
                user_message,
                width_chars=23,
                font_size=10.5,
                marker_size=11,
                min_box_width=0.205,
            )
            text(ax, sx + 0.018, y + 0.057, "◆", size=10.5, color=COLORS["terminal_text"], family=FONT_MONO)
            text(ax, sx + 0.040, y + 0.057, wrapped_agent, size=10.5, color=COLORS["terminal_text"], family=FONT_MONO, linespacing=1.10)
            prompt_line(
                ax,
                sx + 0.018,
                y + 0.017,
                "Re-queue errored jobs.",
                width_chars=23,
                font_size=10.5,
                marker_size=11,
                min_box_width=0.205,
            )
        else:
            prompt_line(
                ax,
                sx + 0.018,
                y + 0.089,
                "Status?",
                width_chars=23,
                font_size=10.5,
                marker_size=11,
                min_box_width=0.205,
            )
            text(ax, sx + 0.018, y + 0.059, "◆", size=10.5, color=COLORS["terminal_text"], family=FONT_MONO)
            text(ax, sx + 0.040, y + 0.059, wrapped_agent, size=10.5, color=COLORS["terminal_text"], family=FONT_MONO, linespacing=1.12)
            prompt_line(
                ax,
                sx + 0.018,
                y + 0.023,
                user_message,
                width_chars=23,
                font_size=10.5,
                marker_size=11,
                min_box_width=0.205,
            )
        if i < 2:
            arrow(ax, (sx + card_w + 0.005, y + h / 2), (sx + card_w + gap - 0.005, y + h / 2), color=COLORS["orange"], dashed=True, zorder=6)

def draw_outputs(ax):
    y = 0.025
    text(ax, 0.06, y + 0.055, "RESULT", size=7.0, color=COLORS["green"], weight="bold")
    text(ax, 0.06, y + 0.035, "computed energies + measured walltimes + errors", size=9.0, weight="bold")
    text(ax, 0.06, y + 0.015, "ranked recommendation", size=7.3, color=COLORS["muted"])

    # Compact result plot: prediction-to-computation dumbbells.
    px, py, pw, ph = 0.435, y + 0.007, 0.210, 0.056
    for i, (pred, actual, color) in enumerate(((0.025, 0.038, COLORS["green"]), (0.072, 0.091, COLORS["yellow"]), (0.137, 0.175, COLORS["orange"]))):
        yy = py + ph - 0.013 - i * 0.019
        ax.plot([px + pred, px + actual], [yy, yy], color=color, lw=2.0, transform=ax.transAxes, zorder=3)
        circle(ax, px + pred, yy, 0.004, facecolor=COLORS["white"], edgecolor=color, linewidth=1.2, zorder=5)
        circle(ax, px + actual, yy, 0.004, facecolor=color, zorder=5)
    text(ax, px, py - 0.005, "predicted ○   measured ●", size=5.8, color=COLORS["muted"])

    file_icon(ax, 0.705, y + 0.018, COLORS["blue"], "results.pkl")
    file_icon(ax, 0.770, y + 0.018, COLORS["green"], "report.csv")
    file_icon(ax, 0.835, y + 0.018, COLORS["orange"], "Psi4 logs")
    pill(ax, 0.895, y + 0.061, "✓", fill=COLORS["green"], width=0.030, height=0.022, size=8)


def panel_height(source_w: float, source_h: float, target_w: float) -> float:
    """Return a target height that preserves the panel's physical aspect ratio."""
    source_aspect = (
        source_w * SOURCE_FIGURE_WIDTH / (source_h * SOURCE_FIGURE_HEIGHT)
    )
    return target_w * FIGURE_WIDTH / (source_aspect * FIGURE_HEIGHT)


def draw_transformed(
    ax,
    draw_function,
    source: tuple[float, float, float, float],
    target: tuple[float, float, float, float],
) -> None:
    """Draw one existing section into a new normalized bounding box."""
    global _DRAW_SCALE_X, _DRAW_SCALE_Y, _FONT_SCALE

    source_x, source_y, source_w, source_h = source
    target_x, target_y, target_w, target_h = target
    scale_x = target_w / source_w
    scale_y = target_h / source_h
    original_transform = ax.transAxes
    original_scales = (_DRAW_SCALE_X, _DRAW_SCALE_Y, _FONT_SCALE)

    mapping = (
        Affine2D()
        .translate(-source_x, -source_y)
        .scale(scale_x, scale_y)
        .translate(target_x, target_y)
    )
    ax.transAxes = mapping + original_transform
    _DRAW_SCALE_X = scale_x
    _DRAW_SCALE_Y = scale_y
    _FONT_SCALE = (
        target_w * FIGURE_WIDTH / (source_w * SOURCE_FIGURE_WIDTH)
    )
    try:
        draw_function(ax)
    finally:
        ax.transAxes = original_transform
        _DRAW_SCALE_X, _DRAW_SCALE_Y, _FONT_SCALE = original_scales


def draw_stage_text(
    ax,
    number: int,
    description: str,
    panel_y: float,
    panel_h: float,
    color: str,
    *,
    compact: bool = False,
    centered: bool = False,
) -> None:
    """Draw a numbered explanatory caption beside a panel."""
    center_y = panel_y + panel_h / 2
    if compact:
        label_x = 0.105
        circle(
            ax,
            label_x,
            center_y,
            0.070,
            facecolor=color,
            edgecolor="white",
            linewidth=1.5,
            zorder=3,
        )
        text(
            ax,
            label_x,
            center_y + 0.040,
            f"{number}.",
            size=16,
            color="white",
            weight="bold",
            ha="center",
            zorder=5,
        )
        ax.plot(
            [label_x - 0.026, label_x + 0.026],
            [center_y + 0.024, center_y + 0.024],
            color="white",
            lw=1.3,
            transform=ax.transAxes,
            zorder=5,
        )
        wrapped = textwrap.fill(description.upper(), width=15)
        text(
            ax,
            label_x,
            center_y - 0.018,
            wrapped,
            size=11.5,
            color="white",
            weight="bold",
            ha="center",
            linespacing=0.95,
            zorder=5,
        )
        return

    if centered:
        label_x = 0.105
        text(
            ax,
            label_x,
            center_y + 0.034,
            f"{number}.",
            size=18,
            color=color,
            weight="bold",
            ha="center",
        )
        ax.plot(
            [label_x - 0.028, label_x + 0.028],
            [center_y + 0.018, center_y + 0.018],
            color=color,
            lw=1.6,
            transform=ax.transAxes,
            zorder=4,
        )
        wrapped = textwrap.fill(description.upper(), width=13)
        text(
            ax,
            label_x,
            center_y + 0.004,
            wrapped,
            size=13,
            color=COLORS["ink"],
            weight="bold",
            ha="center",
            va="top",
            linespacing=1.0,
        )
        return

    label_x = 0.045
    number_size = 14
    description_size = 9.5
    text(ax, label_x, center_y + 0.026, f"{number}.", size=number_size, color=color, weight="bold")
    ax.plot(
        [label_x, label_x + 0.037],
        [center_y + 0.013, center_y + 0.013],
        color=color,
        lw=1.5,
        transform=ax.transAxes,
        zorder=4,
    )
    wrapped = textwrap.fill(description, width=23)
    text(
        ax,
        label_x,
        center_y + 0.002,
        wrapped,
        size=description_size,
        color=COLORS["ink"],
        weight="bold",
        va="top",
        linespacing=1.2,
    )


def make_figure(
    output: Path,
    dpi: int = 240,
    *,
    compact: bool = False,
    centered_labels: bool = False,
) -> list[Path]:
    """Build the figure and save PNG, PDF, and SVG versions."""
    background = COLORS["white"] if centered_labels else COLORS["paper"]
    fig = plt.figure(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT), facecolor=background)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    if compact and centered_labels:
        raise ValueError("compact and centered_labels variants are mutually exclusive")

    if compact:
        target_x = 0.220
        target_w = 0.760
        row_gap = 0.022
        next_top = 0.992
    elif centered_labels:
        target_x = 0.210
        target_w = 0.700
        row_gap = 0.034
        next_top = 0.975
    else:
        text(
            ax,
            0.50,
            0.965,
            "Overview of Agentic Workflow",
            size=19,
            weight="bold",
            ha="center",
        )
        ax.plot(
            [0.37, 0.63],
            [0.947, 0.947],
            color=COLORS["ink"],
            lw=1.6,
            transform=ax.transAxes,
            zorder=4,
        )
        target_x = 0.210
        target_w = 0.700
        row_gap = 0.022
        next_top = 0.915
    panel_specs = (
        (
            draw_initial_prompt,
            (0.10, 0.875, 0.80, 0.120),
            "User prompts coding agent",
            COLORS["orange"],
        ),
        (
            draw_inputs_and_search,
            (0.06, 0.690, 0.88, 0.125),
            "Agent calls error & time estimator models",
            COLORS["blue"],
        ),
        (
            draw_choice_terminal,
            (0.13, 0.496, 0.74, 0.150),
            "User selects computations",
            COLORS["green"],
        ),
        (
            draw_orchestration,
            (0.06, 0.306, 0.88, 0.146),
            "Agent connects to server",
            COLORS["violet"],
        ),
        (
            draw_sessions,
            (0.06, 0.123, 0.88, 0.140),
            "User prompts agent to query results",
            COLORS["orange"],
        ),
    )

    for number, (draw_function, source, description, color) in enumerate(
        panel_specs, start=1
    ):
        target_h = panel_height(source[2], source[3], target_w)
        target_y = next_top - target_h
        target = (target_x, target_y, target_w, target_h)
        draw_transformed(ax, draw_function, source, target)
        draw_stage_text(
            ax,
            number,
            description,
            target_y,
            target_h,
            color,
            compact=compact,
            centered=centered_labels,
        )
        next_top = target_y - row_gap

    output = output.with_suffix("")
    paths = [output.with_suffix(suffix) for suffix in (".png", ".pdf", ".svg")]
    fig.savefig(paths[0], dpi=dpi, facecolor=background)
    fig.savefig(paths[1], facecolor=background)
    fig.savefig(paths[2], facecolor=background)
    plt.close(fig)
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("agentic_workflow_ui"),
        help="Output stem (default: agentic_workflow_ui beside this script)",
    )
    parser.add_argument("--dpi", type=int, default=240, help="PNG resolution (default: 240)")
    variants = parser.add_mutually_exclusive_group()
    variants.add_argument(
        "--compact",
        action="store_true",
        help="Generate the titleless, tighter-margin layout variant",
    )
    variants.add_argument(
        "--centered-labels",
        action="store_true",
        help="Generate a titleless variant with centered stage labels",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = make_figure(
        args.output,
        dpi=args.dpi,
        compact=args.compact,
        centered_labels=args.centered_labels,
    )
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
