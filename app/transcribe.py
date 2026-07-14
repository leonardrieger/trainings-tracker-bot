"""Transkription von Telegram-Sprachnachrichten via Groq Whisper (kostenlos).

Kein nicht-LLM-Fallback möglich (anders als app.llm_parser/app.parser) - schlägt
die Transkription fehl, gibt es schlicht keinen Text zum Weiterverarbeiten.
"""
from __future__ import annotations

import os

import httpx

_GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


def transcribe_voice(audio_bytes: bytes) -> str | None:
    """Transkribiert eine Ogg/Opus-Sprachnachricht zu deutschem Text.

    None bei fehlendem API-Key, API-Fehler oder leerem Ergebnis.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        response = httpx.post(
            _GROQ_TRANSCRIPTION_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            data={"model": "whisper-large-v3-turbo", "language": "de", "response_format": "json"},
            files={"file": ("voice.ogg", audio_bytes, "audio/ogg")},
            timeout=20,
        )
        response.raise_for_status()
        text = response.json().get("text", "").strip()
    except Exception:
        return None
    return text or None
