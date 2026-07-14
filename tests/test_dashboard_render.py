import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dashboard import render_dashboard_html


def test_session_only_uebung_zeigt_zaehler_statt_chart():
    summary = {"Kickboxen": {"count": 5, "last": "2026-07-13T18:00:00"}}
    html = render_dashboard_html([], "token", None, training_days=5, exercise_summary=summary)
    assert "5×" in html
    assert "zuletzt 2026-07-13" in html
    assert 'exercise=Kickboxen' not in html


def test_session_only_aktivitaet_zeigt_absolviert_statt_none():
    recent = [
        {
            "type": "workout",
            "exercise": "Kickboxen",
            "sets": None,
            "reps": None,
            "weight_kg": None,
            "distance_km": None,
            "duration_min": None,
            "logged_at": "2026-07-13T18:00:00",
        }
    ]
    html = render_dashboard_html(recent, "token", None, training_days=1)
    assert "None" not in html
    assert "✓ absolviert" in html


def test_empty_state_hint_fuer_cardio_ist_passend():
    html = render_dashboard_html([], "token", None, training_days=0)
    assert '"30 min 5 km Laufen"' in html
    assert '"Kickboxen"' in html
    assert '"Sparring"' in html


def test_alle_plan_uebungen_erscheinen_auch_ohne_daten():
    html = render_dashboard_html([], "token", None, training_days=0)
    for exercise in ["Kniebeuge", "Klimmzüge", "Pallof Press", "Farmer's Walk"]:
        assert exercise in html
