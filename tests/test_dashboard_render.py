import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dashboard import render_dashboard_html


def test_gewicht_delta_wird_angezeigt():
    html = render_dashboard_html(
        [], "token", {"weight_kg": 83.4}, training_days=0, weight_delta=(85.0, 83.4)
    )
    assert "1,6 kg" in html
    assert "(7 Tage)" in html


def test_gewicht_delta_fehlt_ohne_daten():
    html = render_dashboard_html([], "token", {"weight_kg": 83.4}, training_days=0)
    assert "(7 Tage)" not in html


def test_wiederholen_chips_zeigen_raw_text_und_label():
    last_sets = [
        {
            "exercise": "Bankdrücken", "sets": 3, "reps": 8, "weight_kg": 80,
            "distance_km": None, "duration_min": None, "raw_text": "3x8 80kg Bankdrücken",
            "logged_at": "2026-07-14T10:00:00",
        }
    ]
    html = render_dashboard_html([], "token", None, training_days=0, last_sets=last_sets)
    assert 'data-fill="3x8 80kg Bankdrücken"' in html
    assert "Bankdrücken" in html
    assert '<span class="micro-label">Zuletzt</span>' in html


def test_ohne_last_sets_keine_chips():
    html = render_dashboard_html([], "token", None, training_days=0)
    assert 'class="chip"' not in html


def test_uebungs_datalist_vorhanden():
    html = render_dashboard_html([], "token", None, training_days=0)
    assert '<datalist id="exercise-names">' in html
    assert '<option value="Kniebeuge">' in html
    assert 'list="exercise-names"' in html


def test_session_only_uebung_zeigt_zaehler_statt_chart():
    summary = {"Kickboxen": {"count": 5, "last": "2026-07-13T18:00:00"}}
    html = render_dashboard_html([], "token", None, training_days=5, exercise_summary=summary)
    assert "5×" in html
    assert "zuletzt 13. Jul" in html
    assert "exercise=Kickboxen" not in html  # kein Chart-Bild für Session-Übungen


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


def test_ungetrackte_uebungen_als_kompakte_zeile():
    html = render_dashboard_html([], "token", None, training_days=0)
    assert "Noch nicht getrackt:" in html
    assert "Kniebeuge" in html


def test_leerer_gewichts_zustand_statt_chart():
    html = render_dashboard_html([], "token", None, training_days=0)
    assert "Noch keine Gewichtsdaten" in html
    assert "exercise=Gewicht" not in html


def test_alle_plan_uebungen_erscheinen_auch_ohne_daten():
    html = render_dashboard_html([], "token", None, training_days=0)
    for exercise in ["Kniebeuge", "Klimmzüge", "Pallof Press", "Farmer's Walk"]:
        assert exercise in html


def test_gemischte_sektion_zeigt_karte_und_kompakte_zeile():
    summary = {"Kniebeuge": {"count": 2, "last": "2026-07-14T07:00:00"}}
    html = render_dashboard_html([], "token", None, training_days=1, exercise_summary=summary)
    assert "exercise=Kniebeuge" in html
    assert "Noch nicht getrackt:" in html
    assert "Bankdrücken" in html.split("Noch nicht getrackt:")[1].split("</p>")[0]


def test_chart_karte_hat_onerror_fallback():
    summary = {"Klimmzüge": {"count": 3, "last": "2026-07-14T07:00:00"}}
    html = render_dashboard_html([], "token", None, training_days=1, exercise_summary=summary)
    assert "onerror=" in html
    assert "Noch keine Diagrammdaten" in html


def test_wochen_figur_zeigt_woche():
    html = render_dashboard_html([], "token", None, training_days=0, week_number=5)
    assert "5 / 12" in html


def test_wochen_figur_ohne_startdatum():
    html = render_dashboard_html([], "token", None, training_days=0, week_number=None)
    assert "Woche" in html  # Figur-Label bleibt, Wert ist "–"


def test_deload_note_erscheint_in_woche_7():
    html = render_dashboard_html([], "token", None, training_days=0, week_number=7)
    assert "Deload" in html


def test_kein_deload_in_woche_1():
    html = render_dashboard_html([], "token", None, training_days=0, week_number=1)
    assert "Deload" not in html


def test_wochenstreifen_zeigt_alle_wochentage_und_heutigen_plan():
    montag = date(2026, 7, 20)
    assert montag.weekday() == 0
    html = render_dashboard_html([], "token", None, training_days=0, today=montag)
    for abbr in ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]:
        assert abbr in html
    assert "Tag A" in html  # Hero-Titel für Montag
    assert "Kickboxen" in html  # im Wochenstreifen


def test_wochenstreifen_hebt_heute_hervor():
    mittwoch = date(2026, 7, 22)
    html = render_dashboard_html([], "token", None, training_days=0, today=mittwoch)
    assert '<div class="day today">' in html
    assert "Mittwoch ·" in html  # Eyebrow mit vollem Wochentag


def test_wochenstreifen_zeigt_haken_fuer_trainierte_tage():
    montag = date(2026, 7, 20)
    dienstag = date(2026, 7, 21)
    html = render_dashboard_html(
        [], "token", None, training_days=1, today=dienstag, trained_dates={montag.isoformat()}
    )
    assert html.count("✓") == 1


def test_ohne_today_kein_wochenstreifen():
    html = render_dashboard_html([], "token", None, training_days=0)
    assert '<div class="week-strip">' not in html


def test_flash_wird_angezeigt():
    html = render_dashboard_html([], "token", None, training_days=0, flash="✅ Kniebeuge gespeichert")
    assert 'class="flash"' in html
    assert "✅ Kniebeuge gespeichert" in html


def test_ohne_flash_kein_flash_banner():
    html = render_dashboard_html([], "token", None, training_days=0)
    assert 'class="flash"' not in html


def test_log_formular_und_undo_button_vorhanden():
    html = render_dashboard_html([], "mein-token", None, training_days=0)
    assert '<form class="quick" method="post" action="/dashboard/log?token=mein-token">' in html
    assert 'action="/dashboard/undo?token=mein-token"' in html


def test_vier_tabs_und_ansichten_vorhanden():
    html = render_dashboard_html([], "token", None, training_days=0)
    for view_id in ["view-heute", "view-fortschritt", "view-verlauf", "view-plan"]:
        assert view_id in html
    assert html.count('class="tab"') + html.count('class="tab active"') == 4


def test_plan_tab_zeigt_alle_wochentage_und_werte():
    plan_long = {d: f"Langform {d}" for d in range(7)}
    plan_short = {d: f"Kurz{d}" for d in range(7)}
    html = render_dashboard_html(
        [], "token", None, training_days=0, plan_long=plan_long, plan_short=plan_short
    )
    for d in range(7):
        assert f'name="long_{d}" value="Langform {d}"' in html
        assert f'name="short_{d}" value="Kurz{d}"' in html
    assert 'action="/dashboard/plan?token=token"' in html
    assert 'action="/dashboard/plan/reset?token=token"' in html


def test_view_param_steuert_aktiven_tab():
    html = render_dashboard_html([], "token", None, training_days=0, view="plan")
    assert '<section class="view" id="view-plan">' in html
    assert '<section class="view" id="view-heute" hidden>' in html
    assert 'class="tab active" data-view="plan"' in html


def test_unbekannter_view_param_faellt_auf_heute_zurueck():
    html = render_dashboard_html([], "token", None, training_days=0, view="nonsense")
    assert '<section class="view" id="view-heute">' in html
    assert '<section class="view" id="view-plan" hidden>' in html


def test_verlauf_zeigt_aktivitaeten_als_liste():
    recent = [
        {"type": "workout", "exercise": "Kniebeuge", "sets": 3, "reps": 8, "weight_kg": 87,
         "distance_km": None, "duration_min": None, "logged_at": "2026-07-13T07:30:00"},
        {"type": "bodyweight", "weight_kg": 86.4, "logged_at": "2026-07-13T08:00:00"},
    ]
    html = render_dashboard_html(recent, "token", None, training_days=1)
    assert 'class="activity"' in html
    assert "3×8 · 87 kg" in html
    assert "86,4 kg" in html  # deutsche Komma-Darstellung


def test_pwa_meta_tags_vorhanden():
    html = render_dashboard_html([], "mein-token", None, training_days=0)
    assert 'rel="manifest" href="/manifest.webmanifest?token=mein-token"' in html
    assert 'rel="apple-touch-icon"' in html
    assert "serviceWorker" in html
