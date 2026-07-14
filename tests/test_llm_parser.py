import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import llm_parser


def _fake_groq_response(payload: dict) -> MagicMock:
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"choices": [{"message": {"content": json.dumps(payload)}}]}
    return mock


def test_llm_parse_success_kraft(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    payload = {
        "exercise": "Bankdrücken",
        "is_cardio": False,
        "sets": 2,
        "reps": 8,
        "weight_kg": 80,
        "duration_min": None,
        "distance_km": None,
    }
    with patch("app.llm_parser.httpx.post", return_value=_fake_groq_response(payload)):
        r = llm_parser.parse_message("Gerade habe ich 2 Sets 8 Wiederholungen 80kg Bankdrücken gemacht")
    assert r.exercise == "Bankdrücken"
    assert r.sets == 2
    assert r.reps == 8
    assert r.weight_kg == 80
    assert r.recognized is True
    assert not r.is_cardio


def test_llm_parse_success_cardio(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    payload = {
        "exercise": "Laufen",
        "is_cardio": True,
        "sets": None,
        "reps": None,
        "weight_kg": None,
        "duration_min": 30,
        "distance_km": 5,
    }
    with patch("app.llm_parser.httpx.post", return_value=_fake_groq_response(payload)):
        r = llm_parser.parse_message("War heute 30 Minuten für 5 km laufen")
    assert r.exercise == "Laufen"
    assert r.is_cardio is True
    assert r.duration_min == 30
    assert r.distance_km == 5
    assert r.recognized is True


def test_llm_unbekannte_uebung_vom_modell_wird_verworfen(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    payload = {
        "exercise": "Irgendwas Erfundenes",
        "is_cardio": False,
        "sets": 3,
        "reps": 8,
        "weight_kg": 50,
    }
    with patch("app.llm_parser.httpx.post", return_value=_fake_groq_response(payload)):
        r = llm_parser.parse_message("3 Sätze 8 Wiederholungen 50kg irgendwas")
    assert r.exercise is None
    assert r.recognized is False


def test_fallback_auf_regex_wenn_kein_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    r = llm_parser.parse_message("2 Sets 8 Wiederholungen 80kg Bankdrücken")
    assert r.exercise == "Bankdrücken"
    assert r.sets == 2
    assert r.weight_kg == 80


def test_fallback_auf_regex_bei_api_fehler(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    with patch("app.llm_parser.httpx.post", side_effect=Exception("network down")):
        r = llm_parser.parse_message("2 Sets 8 Wiederholungen 80kg Bankdrücken")
    assert r.exercise == "Bankdrücken"
    assert r.sets == 2


def test_fallback_bei_kaputtem_json(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"choices": [{"message": {"content": "kein json"}}]}
    with patch("app.llm_parser.httpx.post", return_value=mock):
        r = llm_parser.parse_message("2 Sets 8 Wiederholungen 80kg Bankdrücken")
    assert r.exercise == "Bankdrücken"
    assert r.sets == 2
