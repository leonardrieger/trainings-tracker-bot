"""Persönliche Programm-Konfiguration — hier anpassen, um den Bot auf das eigene
Training umzustellen (Wochenplan, Programmlänge, Zielgewicht, Deload-Fenster).

Der restliche Code liest ausschließlich aus diesem Modul; für einen eigenen Plan
muss keine andere Datei angefasst werden. (Die Übungs-Aliase liegen in
``exercises.py``, die Klimmzug-Phasen-Texte in ``reminders.py``.)
"""
from __future__ import annotations

# --- Programm ---------------------------------------------------------------
PROGRAM_LENGTH_WEEKS = 12          # Gesamtlänge des Programms in Wochen
DELOAD_START_WEEK = 6              # erste Deload-Woche (inklusive)
DELOAD_END_WEEK = 8               # letzte Deload-Woche (inklusive)
WEEKLY_TRAINING_TARGET = 6         # geplante Trainingstage pro Woche (für Wochenrückblick)

# --- Zielgewicht (kg) -------------------------------------------------------
TARGET_WEIGHT_MIN = 87.0
TARGET_WEIGHT_MAX = 89.0

# --- Wochenplan (0 = Montag … 6 = Sonntag) ----------------------------------
# Langform: erscheint in der Erinnerung und im Heute-Hero des Dashboards.
TRAINING_PLAN: dict[int, str] = {
    0: "Gym – Tag A (Beine + Druck, schwer)",
    1: "Kickboxen",
    2: "Gym – Tag B (Zug + Nacken) oder Calisthenics-Park",
    3: "Kickboxen",
    4: "Gym – Tag C (Ganzkörper, beinschonend)",
    5: "Sparring – das ist dein HIIT, kein Extra-Cardio",
    6: "Lockerer Dauerlauf (Zone 2) + Mobility",
}

# Kurzform: kompakte Anzeige im Wochenstreifen des Dashboards.
TRAINING_PLAN_SHORT: dict[int, str] = {
    0: "Tag A",
    1: "Kickboxen",
    2: "Tag B",
    3: "Kickboxen",
    4: "Tag C",
    5: "Sparring",
    6: "Laufen",
}

# Wochentag mit dem Klimmzug-Fokus (0 = Montag); an diesem Tag hängt die
# Erinnerung den Klimmzug-Phasen-Hinweis an.
PULLUP_DAY_WEEKDAY = 2  # Mittwoch

# --- Zeitpunkte der automatischen Nachrichten (Europe/Berlin) ---------------
REMINDER_HOUR = 7                  # morgendliche Trainings-Erinnerung
WEEKLY_SUMMARY_WEEKDAY = 6         # Wochenrückblick am Sonntag
WEEKLY_SUMMARY_HOUR = 20
