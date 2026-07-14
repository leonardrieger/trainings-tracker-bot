"""Erzeugt ein Fortschritts-Liniendiagramm (Gewicht/Distanz/Wiederholungen) als PNG-Bytes.

Ruhige, minimalistische Dark-Palette passend zum App-Dashboard: dünne Linie in
gedämpftem Off-White, nur der Endpunkt in Amber betont, dezente Flächenfüllung,
recessive horizontale Gridlines.
"""
from __future__ import annotations

import io
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

SURFACE = "#15171a"
LINE_COLOR = "#c9cbc4"
ACCENT = "#d8a657"
GRID_COLOR = "#212429"
AXIS_COLOR = "#2a2d31"
INK_SECONDARY = "#a5a7a1"
INK_MUTED = "#6d6f6a"
TARGET_BAND_COLOR = "#3f6b52"


def render_progress_chart(
    exercise: str,
    entries: list[dict],
    target_range: tuple[float, float] | None = None,
) -> bytes | None:
    """entries: chronologisch (älteste zuerst), Felder wie aus db.get_history."""
    if not entries:
        return None

    # Metrik nach tatsächlich vorhandenen Daten wählen: Distanz/Dauer für Cardio,
    # Gewicht für Kraft mit Zusatzlast, sonst Wiederholungen (z.B. Klimmzüge im
    # Körpergewicht). So bekommt jede getrackte Übung ein sinnvolles Diagramm statt
    # eines 404 (kaputtes Bild), wenn sie ohne kg geloggt wurde.
    metric_options = [
        ("distance_km", "Distanz (km)"),
        ("duration_min", "Dauer (min)"),
        ("weight_kg", "Gewicht (kg)"),
        ("reps", "Wiederholungen"),
    ]
    metric_key = label = None
    for key, lbl in metric_options:
        if any(e.get(key) is not None for e in entries):
            metric_key, label = key, lbl
            break
    if metric_key is None:
        return None

    points = [
        (datetime.fromisoformat(e["logged_at"]), e[metric_key])
        for e in entries
        if e.get(metric_key) is not None
    ]
    if not points:
        return None
    points.sort(key=lambda p: p[0])
    dates, values = zip(*points)

    fig, ax = plt.subplots(figsize=(6, 3.1))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    if target_range is not None:
        ax.axhspan(target_range[0], target_range[1], color=TARGET_BAND_COLOR, alpha=0.16, linewidth=0)

    lo, hi = min(values), max(values)
    baseline = lo - (hi - lo + 1) * 0.12
    ax.fill_between(dates, values, baseline, color=LINE_COLOR, alpha=0.05, linewidth=0)
    ax.plot(dates, values, color=LINE_COLOR, linewidth=1.6, solid_capstyle="round")
    # Nur der jüngste Punkt wird betont – in Akzentfarbe.
    ax.plot(
        dates[-1], values[-1], marker="o", markersize=6,
        markerfacecolor=ACCENT, markeredgecolor=SURFACE, markeredgewidth=1.5,
    )

    ax.set_ylabel(label, color=INK_MUTED, fontsize=9, labelpad=8)
    ax.tick_params(colors=INK_MUTED, labelsize=8, length=0)
    ax.grid(True, axis="y", color=GRID_COLOR, linewidth=0.8)
    ax.set_axisbelow(True)

    for spine_name, spine in ax.spines.items():
        if spine_name in ("top", "right"):
            spine.set_visible(False)
        else:
            spine.set_color(AXIS_COLOR)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    ax.margins(x=0.02)
    fig.tight_layout(pad=0.6)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=SURFACE, dpi=150)
    plt.close(fig)
    return buf.getvalue()
