"""Reine Logik für Trainings-Erinnerungen, unabhängig von HTTP/DB testbar."""
from __future__ import annotations

from datetime import date, datetime

TRAINING_PLAN: dict[int, str] = {
    0: "Gym – Tag A (Beine + Druck, schwer)",
    1: "Kickboxen",
    2: "Gym – Tag B (Zug + Nacken) oder Calisthenics-Park",
    3: "Kickboxen",
    4: "Gym – Tag C (Ganzkörper, beinschonend)",
    5: "Sparring – das ist dein HIIT, kein Extra-Cardio",
    6: "Lockerer Dauerlauf (Zone 2) + Mobility",
}

REMINDER_HOUR = 7
REMINDER_WINDOW_MINUTES = 10


def reminder_text(day: date) -> str:
    plan = TRAINING_PLAN[day.weekday()]
    return f"🏋️ Heute: {plan}\n\nVergiss nicht zu tracken!"


def should_send_reminder(now: datetime, last_sent: date | None) -> bool:
    if now.hour != REMINDER_HOUR or now.minute >= REMINDER_WINDOW_MINUTES:
        return False
    return last_sent != now.date()
