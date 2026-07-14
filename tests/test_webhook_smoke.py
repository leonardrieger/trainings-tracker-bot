import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("ALLOWED_TELEGRAM_USER_ID", "42")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _update(text: str, user_id: int = 42) -> dict:
    return {"message": {"chat": {"id": user_id}, "from": {"id": user_id}, "text": text}}


def test_start_command():
    with patch("app.main.telegram.send_message") as send:
        r = client.post("/webhook", json=_update("/start"))
        assert r.status_code == 200
        send.assert_called_once()
        assert "42" in send.call_args[0][1]


def test_normal_message_inserts_and_replies():
    with patch("app.main.db.insert_log") as insert, patch("app.main.telegram.send_message") as send:
        r = client.post("/webhook", json=_update("2 Sets 8 Wiederholungen 80kg Bankdrücken"))
        assert r.status_code == 200
        insert.assert_called_once()
        args = insert.call_args[0]
        assert args[0] == 42
        assert args[1].exercise == "Bankdrücken"
        send.assert_called_once_with(42, "✅ Bankdrücken – 2 Sätze × 8 Wdh. @ 80kg")


def test_unauthorized_user_ignored():
    with patch("app.main.db.insert_log") as insert, patch("app.main.telegram.send_message") as send:
        r = client.post("/webhook", json=_update("3 Sätze 8 Wiederholungen 80kg Bankdrücken", user_id=999))
        assert r.status_code == 200
        insert.assert_not_called()
        send.assert_not_called()


def test_verlauf_command():
    fake_entries = [
        {"logged_at": "2026-07-01T10:00:00", "sets": 3, "reps": 8, "weight_kg": 75, "distance_km": None, "duration_min": None}
    ]
    with patch("app.main.db.get_history", return_value=fake_entries) as get_history, patch(
        "app.main.telegram.send_message"
    ) as send:
        r = client.post("/webhook", json=_update("/verlauf Bankdrücken"))
        assert r.status_code == 200
        get_history.assert_called_once()
        send.assert_called_once()
        assert "Bankdrücken" in send.call_args[0][1]


def test_programm_setzen():
    with patch("app.main.db.set_program_start_date") as set_start, patch(
        "app.main.week_number_for", return_value=1
    ), patch("app.main.telegram.send_message") as send:
        r = client.post("/webhook", json=_update("/programm 2026-07-14"))
        assert r.status_code == 200
        set_start.assert_called_once()
        assert "Woche 1/12" in send.call_args[0][1]


def test_programm_ungueltiges_datum():
    with patch("app.main.db.set_program_start_date") as set_start, patch(
        "app.main.telegram.send_message"
    ) as send:
        r = client.post("/webhook", json=_update("/programm nicht-datum"))
        assert r.status_code == 200
        set_start.assert_not_called()
        assert "Format" in send.call_args[0][1]


def test_programm_status_ohne_argument():
    with patch("app.main.db.get_program_start_date", return_value=None), patch(
        "app.main.telegram.send_message"
    ) as send:
        r = client.post("/webhook", json=_update("/programm"))
        assert r.status_code == 200
        assert "Noch kein Startdatum" in send.call_args[0][1]
