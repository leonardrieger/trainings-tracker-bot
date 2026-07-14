"""Supabase-Client-Wrapper für Insert/Query von Trainings-Logs."""
from __future__ import annotations

import json
import os
from datetime import date, timedelta
from functools import lru_cache

from supabase import Client, create_client

from app.config import TRAINING_PLAN, TRAINING_PLAN_SHORT
from app.parser import ParsedWorkout

TABLE = "workout_logs"
BODY_WEIGHT_TABLE = "body_weight_logs"
STATE_TABLE = "bot_state"
TRAINING_PLAN_STATE_KEY = "training_plan"


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


def get_exercise_summary(telegram_user_id: int) -> dict[str, dict]:
    """Pro Übung: Anzahl Einträge + Datum des letzten Eintrags."""
    response = (
        get_client()
        .table(TABLE)
        .select("exercise, logged_at")
        .eq("telegram_user_id", telegram_user_id)
        .execute()
    )
    summary: dict[str, dict] = {}
    for row in response.data:
        entry = summary.setdefault(row["exercise"], {"count": 0, "last": row["logged_at"]})
        entry["count"] += 1
        if row["logged_at"] > entry["last"]:
            entry["last"] = row["logged_at"]
    return summary


def get_last_sets(telegram_user_id: int, limit: int = 4) -> list[dict]:
    """Letzter vollständiger Eintrag je Übung, neueste zuerst (für „Letzten Satz
    wiederholen"-Vorschläge im Dashboard)."""
    rows = (
        get_client()
        .table(TABLE)
        .select("*")
        .eq("telegram_user_id", telegram_user_id)
        .order("logged_at", desc=True)
        .limit(200)
        .execute()
        .data
    )
    seen: set[str] = set()
    result: list[dict] = []
    for row in rows:
        if row["exercise"] in seen or row["exercise"] == "Unbekannt":
            continue
        seen.add(row["exercise"])
        result.append(row)
        if len(result) >= limit:
            break
    return result


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


def get_training_days_count(telegram_user_id: int) -> int:
    response = (
        get_client()
        .table(TABLE)
        .select("logged_at")
        .eq("telegram_user_id", telegram_user_id)
        .execute()
    )
    return len({row["logged_at"][:10] for row in response.data})


def get_workout_dates_in_range(telegram_user_id: int, start: date, end: date) -> set[str]:
    response = (
        get_client()
        .table(TABLE)
        .select("logged_at")
        .eq("telegram_user_id", telegram_user_id)
        .gte("logged_at", start.isoformat())
        .lt("logged_at", (end + timedelta(days=1)).isoformat())
        .execute()
    )
    return {row["logged_at"][:10] for row in response.data}


def get_workout_days_in_range(telegram_user_id: int, start: date, end: date) -> int:
    return len(get_workout_dates_in_range(telegram_user_id, start, end))


def get_weight_change_in_range(
    telegram_user_id: int, start: date, end: date
) -> tuple[float, float] | None:
    """Erster vs. letzter Körpergewicht-Eintrag im Zeitraum, oder None bei <2 Einträgen."""
    response = (
        get_client()
        .table(BODY_WEIGHT_TABLE)
        .select("weight_kg, logged_at")
        .eq("telegram_user_id", telegram_user_id)
        .gte("logged_at", start.isoformat())
        .lt("logged_at", (end + timedelta(days=1)).isoformat())
        .order("logged_at")
        .execute()
    )
    if len(response.data) < 2:
        return None
    return response.data[0]["weight_kg"], response.data[-1]["weight_kg"]


def delete_last_entry(telegram_user_id: int) -> dict | None:
    """Löscht den zuletzt geloggten Eintrag (Workout oder Körpergewicht) und gibt ihn zurück."""
    last_workout = (
        get_client()
        .table(TABLE)
        .select("*")
        .eq("telegram_user_id", telegram_user_id)
        .order("logged_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    last_weight = get_body_weight_history(telegram_user_id, limit=1)

    candidates: list[tuple[str, str, dict]] = []
    if last_workout:
        candidates.append(("workout", TABLE, last_workout[0]))
    if last_weight:
        candidates.append(("bodyweight", BODY_WEIGHT_TABLE, last_weight[0]))
    if not candidates:
        return None

    kind, table, row = max(candidates, key=lambda c: c[2]["logged_at"])
    get_client().table(table).delete().eq("id", row["id"]).execute()
    return {"type": kind, **row}


def get_state(key: str) -> str | None:
    response = get_client().table(STATE_TABLE).select("value").eq("key", key).execute()
    return response.data[0]["value"] if response.data else None


def set_state(key: str, value: str) -> None:
    get_client().table(STATE_TABLE).upsert({"key": key, "value": value}).execute()


def delete_state(key: str) -> None:
    get_client().table(STATE_TABLE).delete().eq("key", key).execute()


def get_last_reminder_date() -> date | None:
    value = get_state("last_reminder_date")
    return date.fromisoformat(value) if value else None


def set_last_reminder_date(d: date) -> None:
    set_state("last_reminder_date", d.isoformat())


def get_last_weekly_summary_date() -> date | None:
    value = get_state("last_weekly_summary_date")
    return date.fromisoformat(value) if value else None


def set_last_weekly_summary_date(d: date) -> None:
    set_state("last_weekly_summary_date", d.isoformat())


def get_program_start_date() -> date | None:
    value = get_state("program_start_date")
    return date.fromisoformat(value) if value else None


def set_program_start_date(d: date) -> None:
    set_state("program_start_date", d.isoformat())


def _merge_training_plan(raw: str | None) -> tuple[dict[int, str], dict[int, str]]:
    """Reine Merge-Logik (kein DB-Zugriff): Override aus der DB pro Wochentag über die
    config.py-Defaults gelegt. Fehlt/kaputt/falscher Typ -> kompletter Fallback auf die
    Defaults; ein einzelner Tag ohne gültige Langform fällt nur für diesen Tag zurück."""
    long_plan, short_plan = dict(TRAINING_PLAN), dict(TRAINING_PLAN_SHORT)
    if not raw:
        return long_plan, short_plan
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return long_plan, short_plan
    if not isinstance(data, dict):
        return long_plan, short_plan

    for day in range(7):
        entry = data.get(str(day))
        if not isinstance(entry, dict):
            continue
        long_text = entry.get("long")
        if not isinstance(long_text, str) or not long_text.strip():
            continue
        long_plan[day] = long_text.strip()
        short_text = entry.get("short")
        short_plan[day] = (
            short_text.strip() if isinstance(short_text, str) and short_text.strip() else long_plan[day]
        )
    return long_plan, short_plan


def get_training_plan() -> tuple[dict[int, str], dict[int, str]]:
    """Aktueller Wochenplan (Lang-/Kurzform): DB-Override falls vorhanden, sonst
    config.py-Default. Kein Schema-Change nötig - liegt als JSON in bot_state."""
    return _merge_training_plan(get_state(TRAINING_PLAN_STATE_KEY))


def set_training_plan(long_plan: dict[int, str], short_plan: dict[int, str]) -> None:
    payload = {str(day): {"long": long_plan[day], "short": short_plan[day]} for day in range(7)}
    set_state(TRAINING_PLAN_STATE_KEY, json.dumps(payload))


def reset_training_plan() -> None:
    delete_state(TRAINING_PLAN_STATE_KEY)
