import sys
from datetime import date
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


def test_ungetrackte_uebungen_als_kompakte_zeile_statt_karten():
    html = render_dashboard_html([], "token", None, training_days=0)
    assert "Noch nicht getrackt: Kniebeuge" in html
    assert html.count('class="empty-card"') == 1  # nur die Körpergewicht-Karte


def test_alle_plan_uebungen_erscheinen_auch_ohne_daten():
    html = render_dashboard_html([], "token", None, training_days=0)
    for exercise in ["Kniebeuge", "Klimmzüge", "Pallof Press", "Farmer's Walk"]:
        assert exercise in html


def test_gemischte_sektion_zeigt_karte_und_kompakte_zeile():
    summary = {"Kniebeuge": {"count": 2, "last": "2026-07-14T07:00:00"}}
    html = render_dashboard_html([], "token", None, training_days=1, exercise_summary=summary)
    assert 'exercise=Kniebeuge' in html
    assert "Noch nicht getrackt:" in html
    assert "Bankdrücken" in html.split("Noch nicht getrackt:")[1].split("</p>")[0]


def test_wochen_stat_tile_zeigt_woche():
    html = render_dashboard_html([], "token", None, training_days=0, week_number=5)
    assert "5/12" in html


def test_wochen_stat_tile_ohne_startdatum():
    html = render_dashboard_html([], "token", None, training_days=0, week_number=None)
    assert "Programmwoche" in html


def test_deload_banner_erscheint_in_woche_7():
    html = render_dashboard_html([], "token", None, training_days=0, week_number=7)
    assert "Deload" in html


def test_kein_deload_banner_in_woche_1():
    html = render_dashboard_html([], "token", None, training_days=0, week_number=1)
    assert "Deload" not in html


def test_wochenkalender_zeigt_alle_wochentage():
    montag = date(2026, 7, 20)
    assert montag.weekday() == 0
    html = render_dashboard_html([], "token", None, training_days=0, today=montag)
    for abbr in ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]:
        assert abbr in html
    assert "Tag A" in html
    assert "Kickboxen" in html


def test_wochenkalender_hebt_heute_hervor():
    mittwoch = date(2026, 7, 22)
    html = render_dashboard_html([], "token", None, training_days=0, today=mittwoch)
    assert '<div class="day-tile today">' in html
    assert "📅 Heute:" in html


def test_wochenkalender_zeigt_haken_fuer_trainierte_tage():
    montag = date(2026, 7, 20)
    dienstag = date(2026, 7, 21)
    html = render_dashboard_html(
        [], "token", None, training_days=1, today=dienstag, trained_dates={montag.isoformat()}
    )
    assert html.count("✓") == 1


def test_ohne_today_kein_kalender():
    html = render_dashboard_html([], "token", None, training_days=0)
    assert 'class="day-tile' not in html


def test_flash_wird_angezeigt():
    html = render_dashboard_html([], "token", None, training_days=0, flash="✅ Kniebeuge gespeichert")
    assert 'class="flash"' in html
    assert "✅ Kniebeuge gespeichert" in html


def test_ohne_flash_kein_flash_banner():
    html = render_dashboard_html([], "token", None, training_days=0)
    assert 'class="flash"' not in html


def test_log_formular_und_undo_button_vorhanden():
    html = render_dashboard_html([], "mein-token", None, training_days=0)
    assert '<form class="log-bar" method="post" action="/dashboard/log?token=mein-token">' in html
    assert '<form class="log-bar" method="post" action="/dashboard/undo?token=mein-token">' in html


def test_pwa_meta_tags_vorhanden():
    html = render_dashboard_html([], "mein-token", None, training_days=0)
    assert 'rel="manifest" href="/manifest.webmanifest?token=mein-token"' in html
    assert 'rel="apple-touch-icon"' in html
    assert "serviceWorker" in html
