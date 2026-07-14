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


def _callback_update(data: str, user_id: int = 42) -> dict:
    return {
        "callback_query": {
            "id": "cbq1",
            "from": {"id": user_id},
            "message": {"chat": {"id": user_id}},
            "data": data,
        }
    }


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


def test_verlauf_ohne_argument_zeigt_tastatur():
    summary = {
        "Bankdrücken": {"count": 2, "last": "2026-07-14T10:00:00"},
        "Kniebeuge": {"count": 1, "last": "2026-07-10T10:00:00"},
    }
    with patch("app.main.db.get_exercise_summary", return_value=summary), patch(
        "app.main.telegram.send_message"
    ) as send:
        r = client.post("/webhook", json=_update("/verlauf"))
    assert r.status_code == 200
    send.assert_called_once()
    keyboard = send.call_args.kwargs["reply_markup"]
    assert keyboard["inline_keyboard"][0][0]["callback_data"] == "v:Bankdrücken"


def test_chart_ohne_argument_zeigt_tastatur():
    summary = {"Bankdrücken": {"count": 2, "last": "2026-07-14T10:00:00"}}
    with patch("app.main.db.get_exercise_summary", return_value=summary), patch(
        "app.main.telegram.send_message"
    ) as send:
        r = client.post("/webhook", json=_update("/chart"))
    assert r.status_code == 200
    keyboard = send.call_args.kwargs["reply_markup"]
    assert keyboard["inline_keyboard"][0][0]["callback_data"] == "c:Bankdrücken"


def test_verlauf_ohne_argument_ohne_daten_zeigt_nutzungshinweis():
    with patch("app.main.db.get_exercise_summary", return_value={}), patch(
        "app.main.telegram.send_message"
    ) as send:
        r = client.post("/webhook", json=_update("/verlauf"))
    assert r.status_code == 200
    assert send.call_args.kwargs.get("reply_markup") is None
    assert "Nutzung" in send.call_args[0][1]


def test_callback_query_chart_routet_zu_chart_und_bestaetigt():
    with patch("app.main.db.get_history", return_value=[{"logged_at": "2026-07-01T10:00:00", "weight_kg": 80}]), patch(
        "app.main.render_progress_chart", return_value=b"fake-png"
    ), patch("app.main.telegram.send_photo") as send_photo, patch(
        "app.main.telegram.answer_callback_query"
    ) as answer:
        r = client.post("/webhook", json=_callback_update("c:Bankdrücken"))
    assert r.status_code == 200
    send_photo.assert_called_once()
    answer.assert_called_once_with("cbq1")


def test_callback_query_verlauf_routet_zu_verlauf_text():
    fake_entries = [
        {"logged_at": "2026-07-01T10:00:00", "sets": 3, "reps": 8, "weight_kg": 75, "distance_km": None, "duration_min": None}
    ]
    with patch("app.main.db.get_history", return_value=fake_entries), patch(
        "app.main.telegram.send_message"
    ) as send, patch("app.main.telegram.answer_callback_query"):
        r = client.post("/webhook", json=_callback_update("v:Kniebeuge"))
    assert r.status_code == 200
    assert "Kniebeuge" in send.call_args[0][1]


def test_callback_query_von_nicht_erlaubtem_nutzer_wird_ignoriert():
    with patch("app.main.telegram.answer_callback_query") as answer, patch(
        "app.main.telegram.send_message"
    ) as send:
        r = client.post("/webhook", json=_callback_update("c:Bankdrücken", user_id=999))
    assert r.status_code == 200
    answer.assert_not_called()
    send.assert_not_called()


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


def test_webhook_secret_fehlt_im_header_wird_ignoriert(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "geheim")
    with patch("app.main.db.insert_log") as insert, patch("app.main.telegram.send_message") as send:
        r = client.post("/webhook", json=_update("3x8 80kg Bankdrücken"))
        assert r.status_code == 200
        insert.assert_not_called()
        send.assert_not_called()


def test_webhook_secret_korrekt_wird_verarbeitet(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "geheim")
    with patch("app.main.db.insert_log") as insert, patch("app.main.telegram.send_message"):
        r = client.post(
            "/webhook",
            json=_update("3x8 80kg Bankdrücken"),
            headers={"X-Telegram-Bot-Api-Secret-Token": "geheim"},
        )
        assert r.status_code == 200
        insert.assert_called_once()


def test_db_fehler_fuehrt_zu_freundlicher_meldung_statt_500():
    with patch("app.main.db.insert_log", side_effect=Exception("supabase down")), patch(
        "app.main.telegram.send_message"
    ) as send:
        r = client.post("/webhook", json=_update("3x8 80kg Bankdrücken"))
        assert r.status_code == 200
        send.assert_called_once()
        assert "schiefgelaufen" in send.call_args[0][1]


def test_undo_loescht_letzten_eintrag():
    deleted = {
        "type": "workout",
        "exercise": "Bankdrücken",
        "sets": 3,
        "reps": 8,
        "weight_kg": 80,
        "logged_at": "2026-07-14T10:00:00",
    }
    with patch("app.main.db.delete_last_entry", return_value=deleted) as delete, patch(
        "app.main.telegram.send_message"
    ) as send:
        r = client.post("/webhook", json=_update("/undo"))
        assert r.status_code == 200
        delete.assert_called_once_with(42)
        assert "🗑️ Gelöscht: Bankdrücken vom 2026-07-14" == send.call_args[0][1]


def test_undo_bodyweight_eintrag():
    deleted = {"type": "bodyweight", "weight_kg": 84.2, "logged_at": "2026-07-14T08:00:00"}
    with patch("app.main.db.delete_last_entry", return_value=deleted), patch(
        "app.main.telegram.send_message"
    ) as send:
        r = client.post("/webhook", json=_update("/undo"))
        assert r.status_code == 200
        assert "Körpergewicht 84.2kg" in send.call_args[0][1]


def test_undo_ohne_eintraege():
    with patch("app.main.db.delete_last_entry", return_value=None), patch(
        "app.main.telegram.send_message"
    ) as send:
        r = client.post("/webhook", json=_update("/undo"))
        assert r.status_code == 200
        assert "Nichts zum Löschen" in send.call_args[0][1]
