"""Baut die HTML-Übersichtsseite (keine Template-Engine, nur f-Strings).

Farben/Layout folgen der validierten Dark-Palette + Komponenten-Regeln aus dem
dataviz-Skill: feste Chart-Surface, Blau als einzige Serie, Stat-Tiles mit
tabular-nums, Karten mit Hairline-Border, Empty-States statt fehlender Karten.
"""
from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import quote

from app.exercises import PLAN_SECTIONS, SESSION_ONLY_EXERCISES
from app.reminders import (
    PROGRAM_LENGTH_WEEKS,
    TRAINING_PLAN,
    TRAINING_PLAN_SHORT,
    WEEKDAY_ABBR,
    is_deload_week,
)

TARGET_WEIGHT_RANGE = "87–89 kg"

_STYLE = """
<style>
  :root {
    --page-plane: #0d0d0d;
    --surface: #1a1a19;
    --ink-primary: #ffffff;
    --ink-secondary: #c3c2b7;
    --ink-muted: #898781;
    --border: rgba(255,255,255,0.10);
    --series-1: #3987e5;
  }
  * { box-sizing: border-box; }
  body {
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    max-width: 1000px; margin: 0 auto; padding: 2rem 1.25rem 4rem;
    background: var(--page-plane); color: var(--ink-primary);
  }
  h1 { margin: 0 0 0.2rem 0; font-size: 1.6rem; }
  .sub { color: var(--ink-secondary); margin: 0 0 0.5rem 0; }
  .tip { color: var(--ink-muted); font-size: 0.82rem; margin: 0 0 1.75rem 0; }
  h2 {
    font-size: 1rem; color: var(--ink-secondary); text-transform: uppercase;
    letter-spacing: 0.04em; margin: 2.25rem 0 0.75rem 0; font-weight: 600;
  }
  .untracked { color: var(--ink-muted); font-size: 0.85rem; margin: 0; }
  .week-row {
    display: grid; grid-template-columns: repeat(7, 1fr); gap: 0.5rem;
    margin-bottom: 0.6rem;
  }
  .day-tile {
    background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    padding: 0.6rem 0.3rem; text-align: center;
  }
  .day-tile.today { border-color: var(--series-1); border-width: 2px; }
  .day-abbr { font-size: 0.72rem; color: var(--ink-muted); text-transform: uppercase; letter-spacing: 0.03em; }
  .day-plan { font-size: 0.8rem; color: var(--ink-primary); margin-top: 0.3rem; font-weight: 500; }
  .day-mark { font-size: 0.78rem; color: #0ca30c; margin-top: 0.3rem; height: 1em; }
  .today-line { color: var(--ink-secondary); font-size: 0.92rem; margin: 0 0 1.5rem 0; }
  .stat-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; }
  .stat-tile {
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 1rem 1.1rem;
  }
  .stat-tile .value {
    font-size: 1.5rem; font-weight: 600; font-variant-numeric: tabular-nums;
    color: var(--ink-primary);
  }
  .stat-tile .label { font-size: 0.8rem; color: var(--ink-muted); margin-top: 0.15rem; }
  .banner {
    border-left: 3px solid #fab219; background: var(--surface); border-radius: 8px;
    padding: 0.8rem 1rem; margin-top: 1rem; font-size: 0.88rem; color: var(--ink-secondary);
  }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1rem; }
  .card {
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 1rem; display: flex; flex-direction: column;
  }
  .card h3 { margin: 0 0 0.6rem 0; font-size: 0.95rem; color: var(--ink-primary); }
  .card img { width: 100%; border-radius: 6px; display: block; }
  .card .session-value {
    font-size: 1.75rem; font-weight: 600; font-variant-numeric: tabular-nums;
    color: var(--ink-primary);
  }
  .card .session-label { font-size: 0.8rem; color: var(--ink-muted); margin-top: 0.2rem; }
  .empty-card {
    border: 1px dashed var(--border); border-radius: 10px; padding: 1.25rem;
    color: var(--ink-muted); font-size: 0.85rem; display: flex; flex-direction: column;
    justify-content: center; min-height: 90px;
  }
  .empty-card h3 { margin: 0 0 0.4rem 0; font-size: 0.95rem; color: var(--ink-secondary); }
  table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; }
  th, td { text-align: left; padding: 0.5rem 0.7rem; border-bottom: 1px solid var(--border); font-size: 0.88rem; }
  th { color: var(--ink-muted); font-weight: 500; }
  td { color: var(--ink-secondary); font-variant-numeric: tabular-nums; }
  .log-bar {
    display: flex; gap: 0.5rem; margin-bottom: 1rem;
  }
  .log-bar input[type="text"] {
    flex: 1; background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    padding: 0.7rem 0.9rem; color: var(--ink-primary); font-size: 1rem;
  }
  .log-bar button {
    background: var(--series-1); border: none; border-radius: 8px; color: #fff;
    padding: 0 1.1rem; font-size: 0.9rem; font-weight: 600; cursor: pointer;
  }
  .log-bar .undo-btn {
    background: var(--surface); border: 1px solid var(--border); color: var(--ink-secondary);
    font-weight: 500;
  }
  .flash {
    border-left: 3px solid var(--series-1); background: var(--surface); border-radius: 8px;
    padding: 0.7rem 1rem; margin-bottom: 1rem; font-size: 0.88rem; color: var(--ink-secondary);
  }
</style>
"""


def _log_bar_html(encoded_token: str) -> str:
    return (
        f'<form class="log-bar" method="post" action="/dashboard/log?token={encoded_token}">'
        '<input type="text" name="text" placeholder=\'z.B. "3x8 100kg Kniebeuge"\' required>'
        '<button type="submit">Eintragen</button>'
        "</form>"
        f'<form class="log-bar" method="post" action="/dashboard/undo?token={encoded_token}">'
        '<button type="submit" class="undo-btn">↩︎ Letzten Eintrag rückgängig machen</button>'
        "</form>"
    )


def _flash_html(flash: str | None) -> str:
    return f'<div class="flash">{flash}</div>' if flash else ""


def _stat_tile(value: str, label: str) -> str:
    return f'<div class="stat-tile"><div class="value">{value}</div><div class="label">{label}</div></div>'


def _week_calendar_html(today: date, trained_dates: set[str]) -> str:
    week_start = today - timedelta(days=today.weekday())
    tiles = []
    for weekday in range(7):
        day = week_start + timedelta(days=weekday)
        classes = "day-tile" + (" today" if day == today else "")
        mark = "✓" if day.isoformat() in trained_dates else ""
        tiles.append(
            f'<div class="{classes}">'
            f'<div class="day-abbr">{WEEKDAY_ABBR[weekday]}</div>'
            f'<div class="day-plan">{TRAINING_PLAN_SHORT[weekday]}</div>'
            f'<div class="day-mark">{mark}</div>'
            f"</div>"
        )
    today_line = f'<p class="today-line">📅 Heute: {TRAINING_PLAN[today.weekday()]}</p>'
    return f'<div class="week-row">{"".join(tiles)}</div>{today_line}'


def _exercise_card(exercise: str, summary: dict, encoded_token: str) -> str:
    info = summary[exercise]

    if exercise in SESSION_ONLY_EXERCISES:
        last_date = info["last"][:10]
        return (
            f'<div class="card"><h3>{exercise}</h3>'
            f'<div class="session-value">{info["count"]}×</div>'
            f'<div class="session-label">geloggt, zuletzt {last_date}</div>'
            f"</div>"
        )

    encoded_exercise = quote(exercise)
    return (
        f'<div class="card"><h3>{exercise}</h3>'
        f'<img src="/dashboard/chart.png?exercise={encoded_exercise}&token={encoded_token}" alt="{exercise} Verlauf">'
        f"</div>"
    )


def _section_html(title: str, section_exercises: list[str], summary: dict, encoded_token: str) -> str:
    tracked = [ex for ex in section_exercises if ex in summary]
    untracked = [ex for ex in section_exercises if ex not in summary]

    parts = [f"<h2>{title}</h2>"]
    if tracked:
        cards = "".join(_exercise_card(ex, summary, encoded_token) for ex in tracked)
        parts.append(f'<div class="grid">{cards}</div>')
    if untracked:
        parts.append(f'<p class="untracked">Noch nicht getrackt: {" · ".join(untracked)}</p>')
    return "".join(parts)


def _activity_row(entry: dict) -> str:
    date = entry["logged_at"][:10]
    if entry["type"] == "bodyweight":
        return f"<tr><td>{date}</td><td>Körpergewicht</td><td>{entry.get('weight_kg', '-')} kg</td></tr>"

    exercise = entry["exercise"]
    if entry.get("distance_km") is not None or entry.get("duration_min") is not None:
        detail = f"{entry.get('distance_km', '-')} km / {entry.get('duration_min', '-')} min"
    elif exercise in SESSION_ONLY_EXERCISES or (
        entry.get("sets") is None and entry.get("reps") is None and entry.get("weight_kg") is None
    ):
        detail = "✓ absolviert"
    else:
        detail = f"{entry.get('sets', '-')}x{entry.get('reps', '-')} @ {entry.get('weight_kg', '-')}kg"
    return f"<tr><td>{date}</td><td>{exercise}</td><td>{detail}</td></tr>"


def render_dashboard_html(
    recent: list[dict],
    token: str,
    latest_weight: dict | None,
    training_days: int,
    exercise_summary: dict[str, dict] | None = None,
    week_number: int | None = None,
    today: date | None = None,
    trained_dates: set[str] | None = None,
    flash: str | None = None,
) -> str:
    encoded_token = quote(token)
    summary = exercise_summary or {}
    exercises_with_data = set(summary.keys())
    week_calendar = _week_calendar_html(today, trained_dates or set()) if today is not None else ""

    weight_value = f"{latest_weight['weight_kg']:g} kg" if latest_weight else "–"
    last_activity = recent[0]["logged_at"][:10] if recent else "–"
    if week_number is None:
        week_value = "–"
    elif week_number <= PROGRAM_LENGTH_WEEKS:
        week_value = f"{week_number}/{PROGRAM_LENGTH_WEEKS}"
    else:
        week_value = "fertig 🎉"

    stat_tiles = "".join(
        [
            _stat_tile(week_value, "Programmwoche"),
            _stat_tile(weight_value, "Aktuelles Gewicht"),
            _stat_tile(TARGET_WEIGHT_RANGE, "Ziel-Gewicht (Woche 12)"),
            _stat_tile(str(training_days), "Trainingstage geloggt"),
            _stat_tile(last_activity, "Letzte Aktivität"),
        ]
    )

    deload_banner = (
        '<div class="banner">📉 Deload-Fenster (Woche 6–8): diese Woche ~60% Gewicht, halbe Sätze.</div>'
        if is_deload_week(week_number)
        else ""
    )

    if latest_weight:
        weight_card = (
            f'<div class="card"><h3>Körpergewicht</h3>'
            f'<img src="/dashboard/chart.png?exercise=Gewicht&token={encoded_token}" alt="Körpergewicht Verlauf">'
            f"</div>"
        )
    else:
        weight_card = (
            '<div class="empty-card"><h3>Körpergewicht</h3>'
            'Noch keine Daten. Schreib z.B. "Gewicht heute 84kg" an den Bot.</div>'
        )

    section_html = []
    covered_exercises: set[str] = set()
    for title, section_exercises in PLAN_SECTIONS:
        covered_exercises.update(section_exercises)
        section_html.append(_section_html(title, section_exercises, summary, encoded_token))

    sonstiges = sorted(exercises_with_data - covered_exercises)
    if sonstiges:
        cards = "".join(_exercise_card(ex, summary, encoded_token) for ex in sonstiges)
        section_html.append(f'<h2>Sonstiges</h2><div class="grid">{cards}</div>')

    rows = "".join(_activity_row(e) for e in recent) or "<tr><td colspan=3>Noch keine Einträge.</td></tr>"

    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Trainings-Tracker</title>
  <link rel="manifest" href="/manifest.webmanifest?token={encoded_token}">
  <link rel="apple-touch-icon" href="/static/icon-192.png">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="theme-color" content="#0d0d0d">
  {_STYLE}
</head>
<body>
  <h1>Trainings-Tracker</h1>
  <p class="sub">Fortschritt über die 12 Wochen</p>

  {_flash_html(flash)}
  {_log_bar_html(encoded_token)}

  {week_calendar}

  <p class="tip">Tipp: Einheiten einfach in freier Sprache eintragen oder an den Bot schreiben, z.B. "3 Sätze 8 Wiederholungen 100kg Kniebeuge" oder "30 min 5 km Laufen".</p>

  <div class="stat-row">{stat_tiles}</div>
  {deload_banner}

  <h2>Körpergewicht</h2>
  <div class="grid">{weight_card}</div>

  {''.join(section_html)}

  <h2>Letzte Aktivitäten</h2>
  <table>
    <thead><tr><th>Datum</th><th>Übung</th><th>Details</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <script>
    if ('serviceWorker' in navigator) {{
      navigator.serviceWorker.register('/sw.js');
    }}
  </script>
</body>
</html>"""
