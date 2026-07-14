"""Freies Frage-Antwort-Chat über Groq (kostenlos), für Nachrichten die nicht als
Trainings-/Körpergewicht-Log erkannt wurden (siehe app.parser.ParsedWorkout.recognized).

Merkt sich die letzten paar Frage-Antwort-Paare (kurzes Konversationsgedächtnis,
global in bot_state gespeichert - der Bot bedient ohnehin nur einen Nutzer), damit
Rückfragen wie "und wie war das letzte Mal?" funktionieren. Nach längerer Inaktivität
wird das Gedächtnis automatisch zurückgesetzt, damit eine Frage am nächsten Morgen nicht
an ein Gespräch vom Vorabend anknüpft.

Fällt bei fehlendem API-Key oder API-Fehler auf einen freundlichen Hinweistext zurück,
analog zum Fallback-Pattern in app.llm_parser.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from app import db
from app.reminders import reminder_text

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_BERLIN = ZoneInfo("Europe/Berlin")

CHAT_HISTORY_TURNS = 3
CHAT_HISTORY_IDLE_MINUTES = 60
_CHAT_HISTORY_KEY = "chat_history"

_SYSTEM_PROMPT = """Du bist ein freundlicher Trainings-Assistent für einen persönlichen \
12-Wochen-Trainingsplan (Kickboxen + Kraft + Ausdauer). Beantworte die Frage kurz und \
konkret auf Deutsch, ausschließlich basierend auf den folgenden Daten. Wenn die Daten \
keine Antwort hergeben, sag das ehrlich statt zu raten.

Wichtig: Der Abschnitt "TRAININGSPLAN FÜR HEUTE" beschreibt nur, was laut Plan ansteht \
- das sagt NICHTS darüber aus, ob es bereits gemacht wurde. Ob und was der Nutzer \
tatsächlich trainiert hat, steht ausschließlich im Abschnitt "BEREITS GETRACKTE \
EINTRÄGE".

{context}
"""

_FALLBACK_TEXT = (
    "🤖 Chat gerade nicht verfügbar. Versuch's gleich nochmal, oder nutze "
    "/verlauf, /chart, /programm."
)


def _format_entry(entry: dict) -> str:
    entry_date = entry["logged_at"][:10]
    if entry["type"] == "bodyweight":
        return f"{entry_date}: Körpergewicht {entry.get('weight_kg', '-')}kg"

    exercise = entry.get("exercise", "?")
    if entry.get("distance_km") is not None or entry.get("duration_min") is not None:
        return f"{entry_date}: {exercise} – {entry.get('distance_km', '-')}km / {entry.get('duration_min', '-')}min"
    if entry.get("sets") is None and entry.get("reps") is None and entry.get("weight_kg") is None:
        return f"{entry_date}: {exercise} – absolviert"
    return f"{entry_date}: {exercise} – {entry.get('sets', '-')}x{entry.get('reps', '-')} @ {entry.get('weight_kg', '-')}kg"


def build_context(user_id: int, today: date, week_number: int | None) -> str:
    plan_long, _ = db.get_training_plan()
    plan = reminder_text(today, week_number, plan_long)
    entries = db.get_recent_activity(user_id, limit=50)
    history = "\n".join(_format_entry(e) for e in entries) if entries else "Noch keine Einträge."
    return (
        f"TRAININGSPLAN FÜR HEUTE (laut Plan, nicht zwingend schon absolviert):\n{plan}\n\n"
        f"BEREITS GETRACKTE EINTRÄGE (neueste zuerst):\n{history}"
    )


def _load_history(now: datetime) -> list[dict]:
    """Letzte Frage-Antwort-Paare, oder leer bei fehlendem/kaputtem/zu altem Verlauf."""
    raw = db.get_state(_CHAT_HISTORY_KEY)
    if not raw:
        return []
    try:
        data = json.loads(raw)
        updated_at = datetime.fromisoformat(data["updated_at"])
        messages = data["messages"]
    except (json.JSONDecodeError, KeyError, ValueError):
        return []
    if now - updated_at > timedelta(minutes=CHAT_HISTORY_IDLE_MINUTES):
        return []
    return messages


def _save_history(now: datetime, messages: list[dict]) -> None:
    trimmed = messages[-2 * CHAT_HISTORY_TURNS :]
    db.set_state(_CHAT_HISTORY_KEY, json.dumps({"updated_at": now.isoformat(), "messages": trimmed}))


def _call_groq_chat(question: str, context: str, history: list[dict]) -> str:
    api_key = os.environ["GROQ_API_KEY"]
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    messages = (
        [{"role": "system", "content": _SYSTEM_PROMPT.format(context=context)}]
        + history
        + [{"role": "user", "content": question}]
    )
    response = httpx.post(
        _GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "messages": messages, "temperature": 0.4, "max_tokens": 300},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def answer_question(user_id: int, question: str, today: date, week_number: int | None) -> str:
    now = datetime.now(_BERLIN)
    history = _load_history(now)
    context = build_context(user_id, today, week_number)
    try:
        answer = _call_groq_chat(question, context, history)
    except Exception:
        return _FALLBACK_TEXT
    _save_history(
        now, history + [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
    )
    return answer
