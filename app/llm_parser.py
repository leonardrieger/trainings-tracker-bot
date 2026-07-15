"""LLM-basiertes Parsing von Trainings-Nachrichten via Groq (kostenlos).

Fällt automatisch auf den Regex-Parser (app.parser) zurück, wenn kein API-Key
gesetzt ist oder der API-Call fehlschlägt (Netzwerk, Rate-Limit) — der Bot
bleibt dadurch auch bei einem LLM-Ausfall funktionsfähig.
"""
from __future__ import annotations

import json
import os

import httpx

from app.exercises import CARDIO_EXERCISES, EXERCISE_ALIASES
from app.parser import ParsedWorkout
from app.parser import parse_message as parse_message_regex

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

_SYSTEM_PROMPT_TEMPLATE = """Du extrahierst Trainingsdaten aus einer kurzen deutschen \
Nachricht und antwortest AUSSCHLIESSLICH mit einem JSON-Objekt, keine Erklärungen, \
kein Markdown.

Erlaubte Übungsnamen (wähle exakt einen davon, exakte Schreibweise, oder null falls \
keiner eindeutig passt):
{exercises}

Falls die Nachricht stattdessen das KÖRPERGEWICHT der Person angibt (z.B. "Gewicht heute
84,2kg", "wiege 83kg"), setze record_type auf "bodyweight" und exercise auf null.

JSON-Felder:
- record_type: "workout" oder "bodyweight"
- exercise: einer der erlaubten Namen oder null (bei "bodyweight" immer null)
- is_cardio: true oder false
- sets: Anzahl Sätze (Zahl) oder null
- reps: Wiederholungen pro Satz (Zahl) oder null
- weight_kg: bei "workout" das Trainingsgewicht, bei "bodyweight" das Körpergewicht (Zahl) oder null
- duration_min: Dauer in Minuten (Zahl) oder null
- distance_km: Distanz in km (Zahl) oder null
"""


def _system_prompt(aliases: dict[str, list[str]] | None = None) -> str:
    names = ", ".join(sorted((aliases if aliases is not None else EXERCISE_ALIASES).keys()))
    return _SYSTEM_PROMPT_TEMPLATE.format(exercises=names)


def _call_groq(text: str, aliases: dict[str, list[str]] | None = None) -> dict:
    api_key = os.environ["GROQ_API_KEY"]
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    response = httpx.post(
        _GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": _system_prompt(aliases)},
                {"role": "user", "content": text},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        },
        timeout=10,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def _as_number(data: dict, key: str) -> float | None:
    value = data.get(key)
    return value if isinstance(value, (int, float)) else None


def parse_message(
    text: str,
    aliases: dict[str, list[str]] | None = None,
    cardio_exercises: set[str] | None = None,
) -> ParsedWorkout:
    aliases = aliases if aliases is not None else EXERCISE_ALIASES
    cardio_exercises = cardio_exercises if cardio_exercises is not None else CARDIO_EXERCISES
    try:
        data = _call_groq(text, aliases)
    except Exception:
        return parse_message_regex(text, aliases, cardio_exercises)

    weight_kg = _as_number(data, "weight_kg")

    if data.get("record_type") == "bodyweight":
        return ParsedWorkout(
            exercise=None,
            is_cardio=False,
            weight_kg=float(weight_kg) if weight_kg is not None else None,
            raw_text=text,
            recognized=weight_kg is not None,
            record_type="bodyweight",
        )

    exercise = data.get("exercise")
    if exercise not in aliases:
        exercise = None

    is_cardio = bool(data.get("is_cardio")) or (exercise in cardio_exercises if exercise else False)

    sets = _as_number(data, "sets")
    reps = _as_number(data, "reps")
    duration_min = _as_number(data, "duration_min")
    distance_km = _as_number(data, "distance_km")

    if is_cardio:
        recognized = exercise is not None and (distance_km is not None or duration_min is not None)
        return ParsedWorkout(
            exercise=exercise or "Laufen",
            is_cardio=True,
            duration_min=duration_min,
            distance_km=distance_km,
            raw_text=text,
            recognized=recognized,
        )

    recognized = exercise is not None and (sets is not None or reps is not None or weight_kg is not None)
    return ParsedWorkout(
        exercise=exercise,
        is_cardio=False,
        sets=int(sets) if sets is not None else None,
        reps=int(reps) if reps is not None else None,
        weight_kg=float(weight_kg) if weight_kg is not None else None,
        raw_text=text,
        recognized=recognized,
    )
