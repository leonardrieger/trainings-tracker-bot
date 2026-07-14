"""Reine Logik für Trainings-Erinnerungen, unabhängig von HTTP/DB testbar.

Programm-spezifische Werte (Wochenplan, Programmlänge, Deload-Fenster, Zeitpunkte)
kommen aus ``app.config`` und werden hier für Rückwärtskompatibilität re-exportiert.
"""
from __future__ import annotations

from datetime import date, datetime

from app.config import (
    DELOAD_END_WEEK,
    DELOAD_START_WEEK,
    PROGRAM_LENGTH_WEEKS,
    PULLUP_DAY_WEEKDAY,
    REMINDER_HOUR,
    TRAINING_PLAN,
    TRAINING_PLAN_SHORT,
    WEEKLY_SUMMARY_HOUR,
    WEEKLY_SUMMARY_WEEKDAY,
    WEEKLY_TRAINING_TARGET,
)

WEEKDAY_ABBR = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

TAG_B_WEEKDAY = PULLUP_DAY_WEEKDAY  # Wochentag mit Klimmzug-Fokus
REMINDER_WINDOW_MINUTES = 10


def week_number_for(today: date, start_date: date | None) -> int | None:
    """1-basiert; None wenn kein Startdatum gesetzt oder Start in der Zukunft liegt."""
    if start_date is None or today < start_date:
        return None
    return (today - start_date).days // 7 + 1


def klimmzug_phase_hint(week_number: int | None) -> str | None:
    if week_number is None or week_number > PROGRAM_LENGTH_WEEKS:
        return None
    if week_number <= 4:
        return "Klimmzug-Programm: 5 Sätze × (Max-2) Wdh., 3 min Pause. +1 Wdh./Satz pro Woche, wenn sauber."
    if week_number <= 8:
        return "Klimmzug-Programm: neuer Max-Test fällig, dann 5×(Max-2) + 1 Satz Negative Klimmzüge×5."
    return "Klimmzug-Programm: ab 10 sauberen Wdh. → Zusatzgewicht (2,5-5kg), 4×6."


def is_deload_week(week_number: int | None) -> bool:
    return week_number is not None and DELOAD_START_WEEK <= week_number <= DELOAD_END_WEEK


def reminder_text(day: date, week_number: int | None = None) -> str:
    plan = TRAINING_PLAN[day.weekday()]
    header = f"🏋️ Heute: {plan}"
    if week_number is not None and week_number <= PROGRAM_LENGTH_WEEKS:
        header += f" (Woche {week_number}/{PROGRAM_LENGTH_WEEKS})"

    lines = [header]
    if day.weekday() == TAG_B_WEEKDAY:
        hint = klimmzug_phase_hint(week_number)
        if hint:
            lines.append(hint)
    if is_deload_week(week_number):
        lines.append(
            f"📉 Deload-Fenster (Woche {DELOAD_START_WEEK}-{DELOAD_END_WEEK}): "
            "diese Woche ~60% Gewicht, halbe Sätze einplanen."
        )
    lines.append("Vergiss nicht zu tracken!")
    return "\n\n".join(lines)


def should_send_reminder(now: datetime, last_sent: date | None) -> bool:
    if now.hour != REMINDER_HOUR or now.minute >= REMINDER_WINDOW_MINUTES:
        return False
    return last_sent != now.date()


def should_send_weekly_summary(now: datetime, last_sent: date | None) -> bool:
    if now.weekday() != WEEKLY_SUMMARY_WEEKDAY:
        return False
    if now.hour != WEEKLY_SUMMARY_HOUR or now.minute >= REMINDER_WINDOW_MINUTES:
        return False
    return last_sent != now.date()


def weekly_summary_text(training_days: int, weight_change: tuple[float, float] | None) -> str:
    lines = ["📊 Wochenrückblick", f"Trainingstage geloggt: {training_days} von {WEEKLY_TRAINING_TARGET} geplant"]
    if weight_change is not None:
        start, end = weight_change
        delta = end - start
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
        lines.append(f"Gewicht: {start:g} → {end:g} kg ({arrow} {abs(delta):.1f} kg)")
    strong = training_days >= WEEKLY_TRAINING_TARGET - 1
    lines.append("Stark durchgezogen! 💪" if strong else "Nächste Woche wieder mehr Einheiten schaffen 💪")
    return "\n".join(lines)
