import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import chat


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
    with patch("app.chat.db.get_recent_activity", return_value=entries) as get_recent:
        context = chat.build_context(42, date(2026, 7, 15), week_number=3)
    get_recent.assert_called_once_with(42, limit=50)
    assert "Gym – Tag B" in context  # Mittwoch 2026-07-15 ist Tag B
    assert "TRAININGSPLAN FÜR HEUTE" in context
    assert "BEREITS GETRACKTE EINTRÄGE" in context
    assert "Bankdrücken – 3x8 @ 80kg" in context


def test_build_context_ohne_eintraege():
    with patch("app.chat.db.get_recent_activity", return_value=[]):
        context = chat.build_context(42, date(2026, 7, 14), week_number=None)
    assert "Noch keine Einträge." in context


def test_answer_question_erfolg(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    with patch("app.chat.db.get_recent_activity", return_value=[]), patch(
        "app.chat.httpx.post", return_value=_fake_groq_response("Heute steht Kickboxen an.")
    ):
        answer = chat.answer_question(42, "Was steht heute an?", date(2026, 7, 14), week_number=1)
    assert answer == "Heute steht Kickboxen an."


def test_answer_question_ohne_api_key_fallback(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with patch("app.chat.db.get_recent_activity", return_value=[]):
        answer = chat.answer_question(42, "Was steht heute an?", date(2026, 7, 14), week_number=1)
    assert "nicht verfügbar" in answer


def test_answer_question_bei_api_fehler_fallback(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    with patch("app.chat.db.get_recent_activity", return_value=[]), patch(
        "app.chat.httpx.post", side_effect=Exception("network down")
    ):
        answer = chat.answer_question(42, "Was steht heute an?", date(2026, 7, 14), week_number=1)
    assert "nicht verfügbar" in answer
