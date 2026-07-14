import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import transcribe


def _fake_groq_response(text: str) -> MagicMock:
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"text": text}
    return mock


def test_transcribe_voice_erfolg(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    with patch("app.transcribe.httpx.post", return_value=_fake_groq_response("3x8 80kg Bankdrücken")):
        result = transcribe.transcribe_voice(b"fake-audio-bytes")
    assert result == "3x8 80kg Bankdrücken"


def test_transcribe_voice_trimmt_whitespace(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    with patch("app.transcribe.httpx.post", return_value=_fake_groq_response("  Kniebeuge  ")):
        result = transcribe.transcribe_voice(b"fake-audio-bytes")
    assert result == "Kniebeuge"


def test_transcribe_voice_ohne_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    result = transcribe.transcribe_voice(b"fake-audio-bytes")
    assert result is None


def test_transcribe_voice_bei_api_fehler(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    with patch("app.transcribe.httpx.post", side_effect=Exception("network down")):
        result = transcribe.transcribe_voice(b"fake-audio-bytes")
    assert result is None


def test_transcribe_voice_leeres_ergebnis(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    with patch("app.transcribe.httpx.post", return_value=_fake_groq_response("")):
        result = transcribe.transcribe_voice(b"fake-audio-bytes")
    assert result is None
