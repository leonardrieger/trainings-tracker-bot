"""Erzeugt ein Fortschritts-Liniendiagramm (Gewicht oder Distanz über Zeit) als PNG-Bytes.

Farben/Mark-Specs folgen der validierten Dark-Palette (dataviz-Skill): dunkle
Chart-Surface, ein Blauton als einzige Serie, recessive Gridlines/Achsen.
"""
from __future__ import annotations

import io
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURFACE = "#1a1a19"
LINE_COLOR = "#3987e5"
GRID_COLOR = "#2c2c2a"
AXIS_COLOR = "#383835"
INK_PRIMARY = "#ffffff"
INK_SECONDARY = "#c3c2b7"
INK_MUTED = "#898781"
TARGET_BAND_COLOR = "#199e70"


def render_progress_chart(
    exercise: str,
    entries: list[dict],
    target_range: tuple[float, float] | None = None,
) -> bytes | None:
    """entries: chronologisch (älteste zuerst), Felder wie aus db.get_history."""
    if not entries:
        return None

    is_cardio = any(e.get("distance_km") is not None for e in entries)
    metric_key = "distance_km" if is_cardio else "weight_kg"
    label = "Distanz (km)" if is_cardio else "Gewicht (kg)"

    points = [
        (datetime.fromisoformat(e["logged_at"]), e[metric_key])
        for e in entries
        if e.get(metric_key) is not None
    ]
    if not points:
        return None
    points.sort(key=lambda p: p[0])
    dates, values = zip(*points)

    fig, ax = plt.subplots(figsize=(6, 4))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    if target_range is not None:
        ax.axhspan(target_range[0], target_range[1], color=TARGET_BAND_COLOR, alpha=0.15, linewidth=0)

    ax.plot(
        dates,
        values,
        color=LINE_COLOR,
        linewidth=2,
        marker="o",
        markersize=8,
        markerfacecolor=LINE_COLOR,
        markeredgecolor=SURFACE,
        markeredgewidth=1.5,
    )

    ax.set_title(f"{exercise} – Fortschritt", color=INK_PRIMARY, fontsize=13, pad=12)
    ax.set_ylabel(label, color=INK_SECONDARY, fontsize=10)
    ax.tick_params(colors=INK_MUTED, labelsize=9)
    ax.grid(True, color=GRID_COLOR, linewidth=0.8)
    ax.set_axisbelow(True)

    for spine_name, spine in ax.spines.items():
        if spine_name in ("top", "right"):
            spine.set_visible(False)
        else:
            spine.set_color(AXIS_COLOR)

    fig.autofmt_xdate()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=SURFACE)
    plt.close(fig)
    return buf.getvalue()
