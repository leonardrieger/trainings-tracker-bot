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

TAG_B_WEEKDAY = 2  # Mittwoch: Klimmzug-Tag

REMINDER_HOUR = 7
REMINDER_WINDOW_MINUTES = 10

WEEKLY_SUMMARY_WEEKDAY = 6  # Sonntag
WEEKLY_SUMMARY_HOUR = 20

PROGRAM_LENGTH_WEEKS = 12


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
    return week_number is not None and 6 <= week_number <= 8


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
        lines.append("📉 Deload-Fenster (Woche 6-8): diese Woche ~60% Gewicht, halbe Sätze einplanen.")
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
    lines = ["📊 Wochenrückblick", f"Trainingstage geloggt: {training_days} von 6 geplant"]
    if weight_change is not None:
        start, end = weight_change
        delta = end - start
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
        lines.append(f"Gewicht: {start:g} → {end:g} kg ({arrow} {abs(delta):.1f} kg)")
    lines.append("Stark durchgezogen! 💪" if training_days >= 5 else "Nächste Woche wieder mehr Einheiten schaffen 💪")
    return "\n".join(lines)
