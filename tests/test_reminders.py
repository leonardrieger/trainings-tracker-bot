import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.reminders import (
    TRAINING_PLAN,
    format_weight_delta,
    is_deload_week,
    klimmzug_phase_hint,
    reminder_text,
    should_send_reminder,
    should_send_weekly_summary,
    week_number_for,
    weekly_summary_text,
)


def test_richtige_stunde_noch_nicht_gesendet():
    now = datetime(2026, 7, 20, 7, 5)  # Montag
    assert should_send_reminder(now, last_sent=None) is True


def test_heute_schon_gesendet():
    now = datetime(2026, 7, 20, 7, 5)
    assert should_send_reminder(now, last_sent=date(2026, 7, 20)) is False


def test_falsche_stunde():
    now = datetime(2026, 7, 20, 12, 0)
    assert should_send_reminder(now, last_sent=None) is False


def test_ausserhalb_des_zeitfensters_innerhalb_der_stunde():
    now = datetime(2026, 7, 20, 7, 15)
    assert should_send_reminder(now, last_sent=None) is False


def test_frueherer_tag_erlaubt_erneutes_senden():
    now = datetime(2026, 7, 20, 7, 5)
    assert should_send_reminder(now, last_sent=date(2026, 7, 19)) is True


def test_reminder_text_enthaelt_montags_plan():
    montag = date(2026, 7, 20)
    assert montag.weekday() == 0
    text = reminder_text(montag)
    assert TRAINING_PLAN[0] in text
    assert "Heute:" in text


def test_reminder_text_mit_explizitem_plan_override():
    montag = date(2026, 7, 20)
    custom_plan = {0: "Individueller Montags-Plan", 1: "x", 2: "x", 3: "x", 4: "x", 5: "x", 6: "x"}
    text = reminder_text(montag, plan=custom_plan)
    assert "Individueller Montags-Plan" in text
    assert TRAINING_PLAN[0] not in text


def test_format_weight_delta_abnahme():
    assert format_weight_delta(85.0, 83.4) == "↓ 1.6 kg"


def test_format_weight_delta_zunahme():
    assert format_weight_delta(83.4, 85.0) == "↑ 1.6 kg"


def test_format_weight_delta_unveraendert():
    assert format_weight_delta(84.0, 84.0) == "→ 0.0 kg"


def test_week_number_vor_start_ist_none():
    assert week_number_for(date(2026, 7, 10), date(2026, 7, 14)) is None


def test_week_number_am_starttag_ist_1():
    assert week_number_for(date(2026, 7, 14), date(2026, 7, 14)) == 1


def test_week_number_nach_7_tagen_ist_2():
    assert week_number_for(date(2026, 7, 21), date(2026, 7, 14)) == 2


def test_week_number_ohne_startdatum_ist_none():
    assert week_number_for(date(2026, 7, 14), None) is None


def test_klimmzug_phase_woche_1_bis_4():
    hint = klimmzug_phase_hint(3)
    assert hint is not None
    assert "Max-2" in hint


def test_klimmzug_phase_woche_5_bis_8():
    hint = klimmzug_phase_hint(6)
    assert "Max-Test" in hint


def test_klimmzug_phase_woche_9_bis_12():
    hint = klimmzug_phase_hint(10)
    assert "Zusatzgewicht" in hint


def test_klimmzug_phase_ohne_wochenzahl_ist_none():
    assert klimmzug_phase_hint(None) is None


def test_klimmzug_phase_nach_programmende_ist_none():
    assert klimmzug_phase_hint(14) is None


def test_deload_fenster_woche_6_bis_8():
    assert is_deload_week(6) is True
    assert is_deload_week(8) is True
    assert is_deload_week(5) is False
    assert is_deload_week(9) is False
    assert is_deload_week(None) is False


def test_reminder_text_mittwoch_enthaelt_klimmzug_hinweis():
    mittwoch = date(2026, 7, 22)
    assert mittwoch.weekday() == 2
    text = reminder_text(mittwoch, week_number=2)
    assert "Klimmzug-Programm" in text
    assert "(Woche 2/12)" in text


def test_reminder_text_montag_ohne_klimmzug_hinweis():
    montag = date(2026, 7, 20)
    text = reminder_text(montag, week_number=2)
    assert "Klimmzug-Programm" not in text


def test_reminder_text_deload_woche_enthaelt_hinweis():
    montag = date(2026, 7, 20)
    text = reminder_text(montag, week_number=7)
    assert "Deload" in text


def test_should_send_weekly_summary_sonntag_20_uhr():
    sonntag = datetime(2026, 7, 19, 20, 5)
    assert sonntag.weekday() == 6
    assert should_send_weekly_summary(sonntag, last_sent=None) is True


def test_should_send_weekly_summary_falscher_wochentag():
    samstag = datetime(2026, 7, 18, 20, 5)
    assert should_send_weekly_summary(samstag, last_sent=None) is False


def test_should_send_weekly_summary_schon_gesendet():
    sonntag = datetime(2026, 7, 19, 20, 5)
    assert should_send_weekly_summary(sonntag, last_sent=date(2026, 7, 19)) is False


def test_weekly_summary_text_ohne_gewichtsaenderung():
    text = weekly_summary_text(training_days=5, weight_change=None)
    assert "5 von 6 geplant" in text
    assert "Gewicht" not in text


def test_weekly_summary_text_mit_gewichtszunahme():
    text = weekly_summary_text(training_days=6, weight_change=(83.0, 83.5))
    assert "↑" in text
    assert "0.5 kg" in text
