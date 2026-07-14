import json
import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import chat
from app.config import TRAINING_PLAN, TRAINING_PLAN_SHORT


def _fake_groq_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"choices": [{"message": {"content": content}}]}
    return mock


def test_format_entry_workout():
    entry = {
        "type": "workout", "exercise": "Bankdrücken", "sets": 3, "reps": 8,
        "weight_kg": 80, "distance_km": None, "duration_min": None,
        "logged_at": "2026-07-14T10:00:00",
    }
    assert chat._format_entry(entry) == "2026-07-14: Bankdrücken – 3x8 @ 80kg"


def test_format_entry_cardio():
    entry = {
        "type": "workout", "exercise": "Laufen", "sets": None, "reps": None,
        "weight_kg": None, "distance_km": 5, "duration_min": 30,
        "logged_at": "2026-07-14T10:00:00",
    }
    assert chat._format_entry(entry) == "2026-07-14: Laufen – 5km / 30min"


def test_format_entry_session_only():
    entry = {
        "type": "workout", "exercise": "Kickboxen", "sets": None, "reps": None,
        "weight_kg": None, "distance_km": None, "duration_min": None,
        "logged_at": "2026-07-14T18:00:00",
    }
    assert chat._format_entry(entry) == "2026-07-14: Kickboxen – absolviert"


def test_format_entry_bodyweight():
    entry = {"type": "bodyweight", "weight_kg": 84.2, "logged_at": "2026-07-14T08:00:00"}
    assert chat._format_entry(entry) == "2026-07-14: Körpergewicht 84.2kg"


def test_build_context_enthaelt_plan_und_verlauf(monkeypatch):
    entries = [
        {
            "type": "workout", "exercise": "Bankdrücken", "sets": 3, "reps": 8,
            "weight_kg": 80, "distance_km": None, "duration_min": None,
            "logged_at": "2026-07-14T10:00:00",
        }
    ]
    with patch("app.chat.db.get_recent_activity", return_value=entries) as get_recent, patch(
        "app.chat.db.get_training_plan", return_value=(TRAINING_PLAN, TRAINING_PLAN_SHORT)
    ):
        context = chat.build_context(42, date(2026, 7, 15), week_number=3)
    get_recent.assert_called_once_with(42, limit=50)
    assert "Gym – Tag B" in context  # Mittwoch 2026-07-15 ist Tag B
    assert "TRAININGSPLAN FÜR HEUTE" in context
    assert "BEREITS GETRACKTE EINTRÄGE" in context
    assert "Bankdrücken – 3x8 @ 80kg" in context


def test_build_context_ohne_eintraege():
    with patch("app.chat.db.get_recent_activity", return_value=[]), patch(
        "app.chat.db.get_training_plan", return_value=(TRAINING_PLAN, TRAINING_PLAN_SHORT)
    ):
        context = chat.build_context(42, date(2026, 7, 14), week_number=None)
    assert "Noch keine Einträge." in context


def test_answer_question_erfolg(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    with patch("app.chat.db.get_recent_activity", return_value=[]), patch(
        "app.chat.db.get_state", return_value=None
    ), patch("app.chat.db.set_state") as set_state, patch(
        "app.chat.httpx.post", return_value=_fake_groq_response("Heute steht Kickboxen an.")
    ):
        answer = chat.answer_question(42, "Was steht heute an?", date(2026, 7, 14), week_number=1)
    assert answer == "Heute steht Kickboxen an."
    set_state.assert_called_once()


def test_answer_question_ohne_api_key_fallback(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with patch("app.chat.db.get_recent_activity", return_value=[]), patch(
        "app.chat.db.get_state", return_value=None
    ), patch("app.chat.db.set_state") as set_state:
        answer = chat.answer_question(42, "Was steht heute an?", date(2026, 7, 14), week_number=1)
    assert "nicht verfügbar" in answer
    set_state.assert_not_called()


def test_answer_question_bei_api_fehler_fallback(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    with patch("app.chat.db.get_recent_activity", return_value=[]), patch(
        "app.chat.db.get_state", return_value=None
    ), patch("app.chat.db.set_state") as set_state, patch(
        "app.chat.httpx.post", side_effect=Exception("network down")
    ):
        answer = chat.answer_question(42, "Was steht heute an?", date(2026, 7, 14), week_number=1)
    assert "nicht verfügbar" in answer
    set_state.assert_not_called()


def test_answer_question_schickt_vorherigen_verlauf_mit(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    stored = json.dumps({
        "updated_at": datetime(2026, 7, 14, 18, 0).isoformat(),
        "messages": [
            {"role": "user", "content": "Was steht heute an?"},
            {"role": "assistant", "content": "Kickboxen."},
        ],
    })
    with patch("app.chat.db.get_recent_activity", return_value=[]), patch(
        "app.chat.db.get_state", return_value=stored
    ), patch("app.chat.db.set_state"), patch(
        "app.chat.datetime"
    ) as mock_dt, patch(
        "app.chat.httpx.post", return_value=_fake_groq_response("Morgen: Gym Tag B.")
    ) as post:
        mock_dt.now.return_value = datetime(2026, 7, 14, 18, 30)
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        chat.answer_question(42, "Und morgen?", date(2026, 7, 14), week_number=1)
    sent_messages = post.call_args.kwargs["json"]["messages"]
    assert {"role": "user", "content": "Was steht heute an?"} in sent_messages
    assert {"role": "assistant", "content": "Kickboxen."} in sent_messages
    assert sent_messages[-1] == {"role": "user", "content": "Und morgen?"}


def test_answer_question_speichert_neues_paar_nach_verlauf(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    with patch("app.chat.db.get_recent_activity", return_value=[]), patch(
        "app.chat.db.get_state", return_value=None
    ), patch("app.chat.db.set_state") as set_state, patch(
        "app.chat.httpx.post", return_value=_fake_groq_response("Kickboxen.")
    ):
        chat.answer_question(42, "Was steht heute an?", date(2026, 7, 14), week_number=1)
    saved = json.loads(set_state.call_args.args[1])
    assert saved["messages"] == [
        {"role": "user", "content": "Was steht heute an?"},
        {"role": "assistant", "content": "Kickboxen."},
    ]


def test_verlauf_wird_nach_drei_paaren_gekappt():
    now = datetime(2026, 7, 14, 18, 0)
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": str(i)} for i in range(10)]
    with patch("app.chat.db.set_state") as set_state:
        chat._save_history(now, history)
    saved = json.loads(set_state.call_args.args[1])
    assert len(saved["messages"]) == 6
    assert saved["messages"][0]["content"] == "4"  # älteste 4 Einträge fallen raus
    assert saved["messages"][-1]["content"] == "9"


def test_verlauf_wird_nach_inaktivitaet_zurueckgesetzt():
    alt = json.dumps({
        "updated_at": datetime(2026, 7, 14, 10, 0).isoformat(),
        "messages": [{"role": "user", "content": "alte frage"}],
    })
    now = datetime(2026, 7, 14, 12, 0)  # 2h später, > 60 min Idle-Fenster
    with patch("app.chat.db.get_state", return_value=alt):
        history = chat._load_history(now)
    assert history == []


def test_verlauf_bleibt_innerhalb_des_idle_fensters():
    aktuell = json.dumps({
        "updated_at": datetime(2026, 7, 14, 11, 45).isoformat(),
        "messages": [{"role": "user", "content": "frage"}],
    })
    now = datetime(2026, 7, 14, 12, 0)  # 15 min später, innerhalb 60 min
    with patch("app.chat.db.get_state", return_value=aktuell):
        history = chat._load_history(now)
    assert history == [{"role": "user", "content": "frage"}]


def test_kaputter_state_wert_wird_wie_kein_verlauf_behandelt():
    with patch("app.chat.db.get_state", return_value="{ubel kaputtes json"):
        history = chat._load_history(datetime(2026, 7, 14, 12, 0))
    assert history == []


def test_leerer_state_wird_wie_kein_verlauf_behandelt():
    with patch("app.chat.db.get_state", return_value=None):
        history = chat._load_history(datetime(2026, 7, 14, 12, 0))
    assert history == []
