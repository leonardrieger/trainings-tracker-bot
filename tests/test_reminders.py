import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.reminders import TRAINING_PLAN, reminder_text, should_send_reminder


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
