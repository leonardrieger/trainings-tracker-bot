import os
import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("ALLOWED_TELEGRAM_USER_ID", "42")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BERLIN = ZoneInfo("Europe/Berlin")


def _fixed_datetime(fixed_now: datetime) -> type:
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    return FixedDatetime


def test_cron_tick_falscher_token():
    r = client.get("/cron/tick?token=falsch")
    assert r.status_code == 200
    assert r.json() == {"ok": False}


def test_cron_tick_ausserhalb_aller_fenster(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "geheim")
    fixed_now = datetime(2026, 7, 21, 12, 0, tzinfo=BERLIN)  # Dienstag Mittag
    with patch("app.main.datetime", _fixed_datetime(fixed_now)), patch(
        "app.main.db.get_last_reminder_date", return_value=date(2020, 1, 1)
    ), patch("app.main.db.get_last_weekly_summary_date", return_value=date(2020, 1, 1)), patch(
        "app.main.telegram.send_message"
    ) as send:
        r = client.get("/cron/tick?token=geheim")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "reminder_sent": False, "weekly_summary_sent": False}
    send.assert_not_called()


def test_cron_tick_reminder_fenster_mocked(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "geheim")
    fixed_now = datetime(2026, 7, 20, 7, 5, tzinfo=BERLIN)  # Montag 7:05
    with patch("app.main.datetime", _fixed_datetime(fixed_now)), patch(
        "app.main.db.get_last_reminder_date", return_value=None
    ), patch("app.main.db.get_last_weekly_summary_date", return_value=date(2020, 1, 1)), patch(
        "app.main.db.get_program_start_date", return_value=None
    ), patch("app.main.db.set_last_reminder_date") as set_reminder, patch(
        "app.main.telegram.send_message"
    ) as send:
        r = client.get("/cron/tick?token=geheim")

    assert r.status_code == 200
    body = r.json()
    assert body["reminder_sent"] is True
    set_reminder.assert_called_once()
    send.assert_called_once()
    assert "Heute:" in send.call_args[0][1]


def test_cron_tick_weekly_summary_fenster_mocked(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "geheim")
    fixed_now = datetime(2026, 7, 19, 20, 5, tzinfo=BERLIN)  # Sonntag 20:05
    with patch("app.main.datetime", _fixed_datetime(fixed_now)), patch(
        "app.main.db.get_last_reminder_date", return_value=date(2020, 1, 1)
    ), patch("app.main.db.get_last_weekly_summary_date", return_value=None), patch(
        "app.main.db.get_workout_days_in_range", return_value=4
    ), patch("app.main.db.get_weight_change_in_range", return_value=None), patch(
        "app.main.db.set_last_weekly_summary_date"
    ) as set_weekly, patch("app.main.telegram.send_message") as send:
        r = client.get("/cron/tick?token=geheim")

    assert r.status_code == 200
    body = r.json()
    assert body["weekly_summary_sent"] is True
    set_weekly.assert_called_once()
    send.assert_called_once()
    assert "Wochenrückblick" in send.call_args[0][1]
