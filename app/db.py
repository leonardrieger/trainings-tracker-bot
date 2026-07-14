"""Supabase-Client-Wrapper für Insert/Query von Trainings-Logs."""
from __future__ import annotations

import os
from functools import lru_cache

from supabase import Client, create_client

from app.parser import ParsedWorkout

TABLE = "workout_logs"


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
