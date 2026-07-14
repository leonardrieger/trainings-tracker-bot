import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.chart import render_progress_chart

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _entry(logged_at, **fields):
    base = {
        "logged_at": logged_at,
        "sets": None,
        "reps": None,
        "weight_kg": None,
        "distance_km": None,
        "duration_min": None,
    }
    base.update(fields)
    return base


def test_kraftuebung_mit_gewicht_rendert_png():
    entries = [
        _entry("2026-07-01T07:00:00", weight_kg=80, reps=8),
        _entry("2026-07-08T07:00:00", weight_kg=85, reps=8),
    ]
    image = render_progress_chart("Bankdrücken", entries)
    assert image is not None
    assert image.startswith(PNG_MAGIC)


def test_koerpergewichtsuebung_ohne_kg_faellt_auf_wiederholungen_zurueck():
    # Klimmzüge als "3x8" geloggt: kein weight_kg, aber reps -> muss trotzdem chartbar sein
    entries = [
        _entry("2026-07-01T07:00:00", sets=3, reps=6),
        _entry("2026-07-08T07:00:00", sets=3, reps=8),
    ]
    image = render_progress_chart("Klimmzüge", entries)
    assert image is not None
    assert image.startswith(PNG_MAGIC)


def test_cardio_nur_mit_dauer_faellt_auf_dauer_zurueck():
    entries = [
        _entry("2026-07-01T07:00:00", duration_min=30),
        _entry("2026-07-08T07:00:00", duration_min=35),
    ]
    image = render_progress_chart("Laufen", entries)
    assert image is not None
    assert image.startswith(PNG_MAGIC)


def test_distanz_hat_vorrang_vor_dauer():
    entries = [
        _entry("2026-07-01T07:00:00", distance_km=5, duration_min=30),
        _entry("2026-07-08T07:00:00", distance_km=6, duration_min=35),
    ]
    image = render_progress_chart("Laufen", entries)
    assert image is not None
    assert image.startswith(PNG_MAGIC)


def test_ohne_jede_zahl_gibt_none():
    entries = [_entry("2026-07-01T07:00:00")]
    assert render_progress_chart("Kickboxen", entries) is None


def test_leere_liste_gibt_none():
    assert render_progress_chart("Kniebeuge", []) is None
