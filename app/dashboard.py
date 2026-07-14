"""Baut die HTML-Übersichtsseite (keine Template-Engine, nur f-Strings + Inline-CSS)."""
from __future__ import annotations

from urllib.parse import quote

_STYLE = """
<style>
  body { font-family: -apple-system, Segoe UI, sans-serif; max-width: 900px; margin: 2rem auto;
         padding: 0 1rem; background: #0f1115; color: #e6e6e6; }
  h1 { margin-bottom: 0.2rem; }
  .sub { color: #9aa0a6; margin-top: 0; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem; }
  .card { background: #1a1d24; border-radius: 10px; padding: 1rem; }
  .card h3 { margin: 0 0 0.5rem 0; }
  .card img { width: 100%; border-radius: 6px; }
  table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; }
  th, td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #2a2e37; font-size: 0.9rem; }
  th { color: #9aa0a6; font-weight: 500; }
</style>
"""


def _activity_row(entry: dict) -> str:
    date = entry["logged_at"][:10]
    if entry["type"] == "bodyweight":
        return f"<tr><td>{date}</td><td>Körpergewicht</td><td>{entry.get('weight_kg', '-')} kg</td></tr>"
    if entry.get("distance_km") is not None or entry.get("duration_min") is not None:
        detail = f"{entry.get('distance_km', '-')} km / {entry.get('duration_min', '-')} min"
    else:
        detail = f"{entry.get('sets', '-')}x{entry.get('reps', '-')} @ {entry.get('weight_kg', '-')}kg"
    return f"<tr><td>{date}</td><td>{entry['exercise']}</td><td>{detail}</td></tr>"


def render_dashboard_html(exercises: list[str], recent: list[dict], token: str) -> str:
    encoded_token = quote(token)
    cards = [
        f"""<div class="card">
          <h3>Körpergewicht</h3>
          <img src="/dashboard/chart.png?exercise=Gewicht&token={encoded_token}" alt="Körpergewicht Verlauf">
        </div>"""
    ]
    for exercise in exercises:
        encoded_exercise = quote(exercise)
        cards.append(
            f"""<div class="card">
              <h3>{exercise}</h3>
              <img src="/dashboard/chart.png?exercise={encoded_exercise}&token={encoded_token}" alt="{exercise} Verlauf">
            </div>"""
        )

    rows = "".join(_activity_row(e) for e in recent) or "<tr><td colspan=3>Noch keine Einträge.</td></tr>"

    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Trainings-Tracker</title>
  {_STYLE}
</head>
<body>
  <h1>Trainings-Tracker</h1>
  <p class="sub">Fortschritt über die 12 Wochen</p>
  <div class="grid">{''.join(cards)}</div>
  <h2>Letzte Aktivitäten</h2>
  <table>
    <thead><tr><th>Datum</th><th>Übung</th><th>Details</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>"""
