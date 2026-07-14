"""Supabase-Client-Wrapper für Insert/Query von Trainings-Logs."""
from __future__ import annotations

import os
from datetime import date
from functools import lru_cache

from supabase import Client, create_client

from app.parser import ParsedWorkout

TABLE = "workout_logs"
BODY_WEIGHT_TABLE = "body_weight_logs"
STATE_TABLE = "bot_state"


@lru_cache
def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


def insert_log(telegram_user_id: int, parsed: ParsedWorkout) -> None:
    get_client().table(TABLE).insert(
        {
            "telegram_user_id": telegram_user_id,
            "exercise": parsed.exercise or "Unbekannt",
            "sets": parsed.sets,
            "reps": parsed.reps,
            "weight_kg": parsed.weight_kg,
            "duration_min": parsed.duration_min,
            "distance_km": parsed.distance_km,
            "raw_text": parsed.raw_text,
        }
    ).execute()


def get_history(telegram_user_id: int, exercise: str, limit: int = 10) -> list[dict]:
    response = (
        get_client()
        .table(TABLE)
        .select("*")
        .eq("telegram_user_id", telegram_user_id)
        .ilike("exercise", exercise)
        .order("logged_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


def list_exercises(telegram_user_id: int) -> list[str]:
    response = (
        get_client()
        .table(TABLE)
        .select("exercise")
        .eq("telegram_user_id", telegram_user_id)
        .execute()
    )
    return sorted({row["exercise"] for row in response.data})


def get_recent_activity(telegram_user_id: int, limit: int = 20) -> list[dict]:
    workouts = (
        get_client()
        .table(TABLE)
        .select("*")
        .eq("telegram_user_id", telegram_user_id)
        .order("logged_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )
    weights = get_body_weight_history(telegram_user_id, limit=limit)
    combined = [{"type": "workout", **w} for w in workouts] + [
        {"type": "bodyweight", **w} for w in weights
    ]
    combined.sort(key=lambda r: r["logged_at"], reverse=True)
    return combined[:limit]


def insert_body_weight(telegram_user_id: int, weight_kg: float, raw_text: str) -> None:
    get_client().table(BODY_WEIGHT_TABLE).insert(
        {
            "telegram_user_id": telegram_user_id,
            "weight_kg": weight_kg,
            "raw_text": raw_text,
        }
    ).execute()


def get_body_weight_history(telegram_user_id: int, limit: int = 10) -> list[dict]:
    response = (
        get_client()
        .table(BODY_WEIGHT_TABLE)
        .select("*")
        .eq("telegram_user_id", telegram_user_id)
        .order("logged_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


def get_last_reminder_date() -> date | None:
    response = (
        get_client().table(STATE_TABLE).select("value").eq("key", "last_reminder_date").execute()
    )
    if not response.data:
        return None
    return date.fromisoformat(response.data[0]["value"])


def set_last_reminder_date(d: date) -> None:
    get_client().table(STATE_TABLE).upsert(
        {"key": "last_reminder_date", "value": d.isoformat()}
    ).execute()
