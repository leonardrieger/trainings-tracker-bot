"""Erzeugt ein Fortschritts-Liniendiagramm (Gewicht oder Distanz über Zeit) als PNG-Bytes."""
from __future__ import annotations

import io
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def render_progress_chart(exercise: str, entries: list[dict]) -> bytes | None:
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
    ax.plot(dates, values, marker="o")
    ax.set_title(f"{exercise} – Fortschritt")
    ax.set_ylabel(label)
    fig.autofmt_xdate()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
