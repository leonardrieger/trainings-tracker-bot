"""Regelbasiertes Parsing von Trainings-Nachrichten in strukturierte Records.

Kein LLM-Call: reine Regex-Extraktion von Zahlen+Einheiten, unabhängig von der
Satzstellung, plus Abgleich der Übung gegen eine bekannte Alias-Liste.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.exercises import CARDIO_EXERCISES, match_exercise

_SETS_RE = re.compile(r"(\d+)\s*(?:sets?|sätze|saetze)\b", re.IGNORECASE)
_REPS_RE = re.compile(r"(\d+)\s*(?:wiederholungen|wdh\.?|reps?)\b", re.IGNORECASE)
_WEIGHT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*kg\b", re.IGNORECASE)
_COMPACT_RE = re.compile(r"(\d+)\s*[x×]\s*(\d+)\b", re.IGNORECASE)
_DISTANCE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*km\b", re.IGNORECASE)
_DURATION_RE = re.compile(r"(\d+)\s*min(?:uten)?\b", re.IGNORECASE)
_BODYWEIGHT_RE = re.compile(r"\b(?:gewicht|wiege|körpergewicht|koerpergewicht)\b", re.IGNORECASE)


@dataclass
class ParsedWorkout:
    exercise: str | None
    is_cardio: bool
    sets: int | None = None
    reps: int | None = None
    weight_kg: float | None = None
    duration_min: float | None = None
    distance_km: float | None = None
    raw_text: str = ""
    recognized: bool = False
    record_type: str = "workout"

    def confirmation_text(self) -> str:
        if self.record_type == "bodyweight":
            if self.weight_kg is None:
                return (
                    "⚠️ Kein Gewicht erkannt. Tipp: \"Gewicht heute 84,2kg\"."
                )
            return f"⚖️ Körpergewicht: {self.weight_kg:g} kg notiert"
        if not self.recognized:
            return (
                "⚠️ Konnte die Übung nicht sicher erkennen. Gespeichert als Rohtext:\n"
                f'"{self.raw_text}"\n\n'
                "Tipp: schreib z.B. \"3 Sätze 8 Wiederholungen 80kg Bankdrücken\" "
                "oder für Cardio \"30 min 5 km Laufen\"."
            )
        if self.is_cardio:
            parts = [f"✅ {self.exercise}"]
            if self.distance_km is not None:
                parts.append(f"{self.distance_km:g} km")
            if self.duration_min is not None:
                parts.append(f"{self.duration_min:g} min")
            return " – ".join(parts) if len(parts) > 1 else parts[0]
        parts = [f"✅ {self.exercise}"]
        detail = []
        if self.sets is not None and self.reps is not None:
            detail.append(f"{self.sets} Sätze × {self.reps} Wdh.")
        elif self.sets is not None:
            detail.append(f"{self.sets} Sätze")
        elif self.reps is not None:
            detail.append(f"{self.reps} Wdh.")
        if self.weight_kg is not None:
            detail.append(f"@ {self.weight_kg:g}kg")
        if detail:
            parts.append(" ".join(detail))
        return " – ".join(parts)


def _to_float(s: str) -> float:
    return float(s.replace(",", "."))


def parse_message(text: str) -> ParsedWorkout:
    weight_match = _WEIGHT_RE.search(text)

    if _BODYWEIGHT_RE.search(text) and weight_match:
        return ParsedWorkout(
            exercise=None,
            is_cardio=False,
            weight_kg=_to_float(weight_match.group(1)),
            raw_text=text,
            recognized=True,
            record_type="bodyweight",
        )

    exercise = match_exercise(text)
    is_cardio = exercise in CARDIO_EXERCISES if exercise else False

    distance_match = _DISTANCE_RE.search(text)
    duration_match = _DURATION_RE.search(text)
    sets_match = _SETS_RE.search(text)
    reps_match = _REPS_RE.search(text)

    # Cardio-Signal auch ohne bekannte Übung erkennen (z.B. "5 km gelaufen")
    if exercise is None and (distance_match or duration_match) and not weight_match:
        is_cardio = True

    if is_cardio:
        distance_km = _to_float(distance_match.group(1)) if distance_match else None
        duration_min = _to_float(duration_match.group(1)) if duration_match else None
        recognized = exercise is not None and (distance_km is not None or duration_min is not None)
        return ParsedWorkout(
            exercise=exercise or "Laufen",
            is_cardio=True,
            duration_min=duration_min,
            distance_km=distance_km,
            raw_text=text,
            recognized=recognized,
        )

    sets = int(sets_match.group(1)) if sets_match else None
    reps = int(reps_match.group(1)) if reps_match else None

    if sets is None and reps is None:
        compact_match = _COMPACT_RE.search(text)
        if compact_match:
            sets = int(compact_match.group(1))
            reps = int(compact_match.group(2))

    weight_kg = _to_float(weight_match.group(1)) if weight_match else None

    recognized = exercise is not None and (sets is not None or reps is not None or weight_kg is not None)

    return ParsedWorkout(
        exercise=exercise,
        is_cardio=False,
        sets=sets,
        reps=reps,
        weight_kg=weight_kg,
        raw_text=text,
        recognized=recognized,
    )
