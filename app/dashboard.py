"""Baut die App-artige Übersichtsseite (keine Template-Engine, nur f-Strings).

Vier Ansichten (Heute / Fortschritt / Verlauf / Plan), unten per Tab-Leiste gewechselt.
Ruhiger, minimalistischer Dark-Look: ein warmer Amber-Akzent sehr sparsam, dünne
große Zahlen mit tabular-nums, Haarlinien statt schwerer Karten.
"""
from __future__ import annotations

import html
from datetime import date, timedelta

from app.config import TARGET_WEIGHT_MAX, TARGET_WEIGHT_MIN
from app.exercises import CARDIO_EXERCISES, EXERCISE_ALIASES, PLAN_SECTIONS, SESSION_ONLY_EXERCISES
from app.reminders import (
    PROGRAM_LENGTH_WEEKS,
    TRAINING_PLAN,
    TRAINING_PLAN_SHORT,
    WEEKDAY_ABBR,
    format_weight_delta,
    is_deload_week,
)
from urllib.parse import quote

_min = f"{TARGET_WEIGHT_MIN:g}".replace(".", ",")
_max = f"{TARGET_WEIGHT_MAX:g}".replace(".", ",")
TARGET_WEIGHT_RANGE = f"{_min}–{_max} kg"

WEEKDAY_FULL = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
_SECTION_TITLES = [title for title, _ in PLAN_SECTIONS]
MONTH_FULL = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]
MONTH_ABBR = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]

# onerror: falls ein Chart doch 404 liefert (Alt-Eintrag ganz ohne Zahlen),
# das kaputte Bild durch eine schlichte Textzeile ersetzen statt Fragezeichen.
_CHART_ONERROR = (
    "this.outerHTML=&#39;&lt;p class=&quot;untracked-line&quot;&gt;"
    "Noch keine Diagrammdaten.&lt;/p&gt;&#39;"
)

_STYLE = """
<style>
  :root {
    --ground: #0e0f11; --surface: #15171a; --surface-2: #1b1e22;
    --line: rgba(255,255,255,.07); --line-strong: rgba(255,255,255,.13);
    --ink: #f3f4f1; --ink-dim: #a5a7a1; --ink-mute: #6d6f6a;
    --accent: #d8a657; --accent-soft: rgba(216,166,87,.14); --good: #6fa77c;
    --radius: 14px; --nav-h: 64px;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: var(--ground); }
  .app {
    max-width: 460px; margin: 0 auto; min-height: 100vh; background: var(--ground);
    color: var(--ink); font-family: -apple-system, "SF Pro Text", "Segoe UI", system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    padding-bottom: calc(var(--nav-h) + env(safe-area-inset-bottom, 0px) + 12px); position: relative;
  }
  .view { padding: 1.5rem 1.35rem 0; }
  .view[hidden] { display: none; }
  .micro-label { font-size: .68rem; text-transform: uppercase; letter-spacing: .16em; color: var(--ink-mute); font-weight: 600; }
  .view-head { margin-bottom: .3rem; }

  .today-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 1.6rem; gap: 1rem; }
  .eyebrow { font-size: .82rem; color: var(--ink-dim); }
  .week-pill {
    font-size: .72rem; color: var(--accent); letter-spacing: .08em; font-variant-numeric: tabular-nums;
    border: 1px solid var(--line-strong); padding: .28rem .55rem; border-radius: 999px; white-space: nowrap;
  }
  .hero { font-size: clamp(2rem, 8.5vw, 2.5rem); font-weight: 300; line-height: 1.05; letter-spacing: -.025em; margin: 0; text-wrap: balance; }
  .hero-sub { margin: .5rem 0 0; color: var(--ink-dim); font-size: 1rem; }
  .note {
    margin: 1.1rem 0 0; padding: .6rem .85rem; border-left: 2px solid var(--accent);
    background: var(--accent-soft); border-radius: 0 8px 8px 0; font-size: .82rem; color: var(--ink-dim);
  }

  .chips { margin: 1.75rem 0 0; }
  .chip-row { display: flex; gap: .5rem; overflow-x: auto; margin-top: .7rem; padding-bottom: .1rem; }
  .chip {
    flex: 0 0 auto; background: var(--surface); border: 1px solid var(--line); border-radius: 999px;
    padding: .5rem .9rem; color: var(--ink-dim); font-size: .82rem; font-family: inherit;
    white-space: nowrap; cursor: pointer;
  }
  .chip:active { transform: scale(.97); }

  .quick { display: flex; gap: .5rem; margin: 1.75rem 0 .5rem; }
  .quick input {
    flex: 1; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
    padding: .85rem 1rem; color: var(--ink); font-size: .95rem; font-family: inherit;
  }
  .quick input::placeholder { color: var(--ink-mute); }
  .quick input:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; border-color: transparent; }
  .quick button { border: none; background: var(--ink); color: var(--ground); border-radius: var(--radius); width: 52px; font-size: 1.2rem; cursor: pointer; display: grid; place-items: center; }
  .quick button:active { transform: scale(.96); }
  .undo-form { margin: 0; }
  .undo { background: none; border: none; color: var(--ink-mute); font-size: .8rem; padding: .2rem 0; cursor: pointer; font-family: inherit; }
  .undo:hover { color: var(--ink-dim); }
  .flash { margin: .8rem 0 0; padding: .7rem .9rem; border-radius: 10px; background: var(--accent-soft); color: var(--accent); font-size: .85rem; border: 1px solid rgba(216,166,87,.22); }

  .week-strip { display: grid; grid-template-columns: repeat(7, 1fr); gap: .3rem; margin: 2rem 0 0; padding-top: 1.6rem; border-top: 1px solid var(--line); }
  .day { text-align: center; }
  .day .d-abbr { font-size: .66rem; text-transform: uppercase; letter-spacing: .06em; color: var(--ink-mute); }
  .day .d-plan { font-size: .66rem; color: var(--ink-dim); margin-top: .5rem; line-height: 1.2; }
  .day .d-mark { height: .9rem; margin-top: .4rem; font-size: .72rem; color: var(--good); }
  .day.today .d-abbr { color: var(--accent); }
  .day.today .d-plan { color: var(--ink); }
  .day.today .dot { width: 5px; height: 5px; border-radius: 50%; background: var(--accent); margin: .45rem auto 0; }

  .today-log { margin-top: 2.1rem; padding-top: 1.5rem; border-top: 1px solid var(--line); }
  .today-log .micro-label { display: block; margin-bottom: .9rem; }
  .log-row { display: flex; align-items: baseline; justify-content: space-between; padding: .55rem 0; border-bottom: 1px solid var(--line); gap: 1rem; }
  .log-row:last-child { border-bottom: none; }
  .log-row .l-name { font-size: .95rem; color: var(--ink); }
  .log-row .l-detail { font-size: .85rem; color: var(--ink-dim); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .log-row .l-detail.done, .activity .a-detail.done { color: var(--good); }
  .empty-line { color: var(--ink-mute); font-size: .88rem; margin: 0; }

  .figures { display: grid; grid-template-columns: repeat(3, 1fr); margin: 1rem 0 .4rem; }
  .figure { padding: .2rem 0; position: relative; }
  .figure + .figure { padding-left: 1rem; }
  .figure + .figure::before { content: ""; position: absolute; left: 0; top: .3rem; bottom: .3rem; width: 1px; background: var(--line); }
  .figure .f-val { font-size: clamp(1.7rem, 7.5vw, 2.1rem); font-weight: 300; letter-spacing: -.02em; font-variant-numeric: tabular-nums; line-height: 1; }
  .figure .f-unit { font-size: .9rem; color: var(--ink-dim); font-weight: 300; }
  .figure .f-label { font-size: .66rem; text-transform: uppercase; letter-spacing: .1em; color: var(--ink-mute); margin-top: .55rem; }

  .chart-block { margin-top: 2rem; padding-top: 1.6rem; border-top: 1px solid var(--line); }
  .chart-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: .2rem; }
  .chart-head h2 { font-size: 1.05rem; font-weight: 500; margin: 0; letter-spacing: -.01em; }
  .chart-cap { font-size: .74rem; color: var(--ink-mute); margin: .3rem 0 0; }
  img.chart { width: 100%; display: block; border-radius: 10px; margin-top: .7rem; }

  .section-label { display: block; margin: 2.2rem 0 .2rem; }
  .chart-grid { display: grid; gap: 1rem; margin-top: .9rem; }
  .mini-card h3 { font-size: .9rem; font-weight: 500; color: var(--ink-dim); margin: 0 0 .1rem; }
  .mini-card h3 .muted { color: var(--ink-mute); font-weight: 400; }
  .count-meta { font-size: .88rem; color: var(--ink-dim); margin: .35rem 0 0; }
  .count-meta .count-num { color: var(--ink); font-variant-numeric: tabular-nums; }
  .untracked-line { font-size: .82rem; color: var(--ink-mute); margin: 1rem 0 0; line-height: 1.5; }

  .activity { list-style: none; margin: 1.2rem 0 0; padding: 0; }
  .activity li { display: grid; grid-template-columns: auto 1fr auto auto; align-items: baseline; gap: .9rem; padding: .8rem 0; border-bottom: 1px solid var(--line); }
  .activity .a-date { font-size: .78rem; color: var(--ink-mute); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .activity .a-name { font-size: .95rem; color: var(--ink); }
  .activity .a-detail { font-size: .85rem; color: var(--ink-dim); font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap; }
  .a-edit { padding: 0; font-size: .85rem; }
  .entry-edit {
    grid-column: 1 / -1; margin-top: .4rem; padding: .8rem;
    background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
  }
  .entry-fields { display: grid; grid-template-columns: repeat(3, 1fr); gap: .5rem; margin-bottom: .6rem; }
  .entry-fields .ef span { display: block; font-size: .62rem; text-transform: uppercase; letter-spacing: .08em; color: var(--ink-mute); margin-bottom: .3rem; }
  .entry-fields .ef-wide { grid-column: 1 / -1; }
  .entry-fields input {
    display: block; width: 100%; background: var(--surface-2); border: 1px solid var(--line); border-radius: 10px;
    padding: .55rem .65rem; color: var(--ink); font-size: .88rem; font-family: inherit; font-variant-numeric: tabular-nums;
  }
  .entry-fields input:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; border-color: transparent; }
  .entry-delete { margin: .5rem 0 0; text-align: right; }

  .plan-row { margin: 0 0 1.3rem; }
  .plan-day { display: block; font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; color: var(--ink-mute); margin-bottom: .5rem; }
  .plan-row input {
    display: block; width: 100%; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
    padding: .7rem .85rem; color: var(--ink); font-size: .9rem; font-family: inherit; margin-bottom: .4rem;
  }
  .plan-row input:last-child { margin-bottom: 0; font-size: .8rem; color: var(--ink-dim); }
  .plan-row input:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; border-color: transparent; }
  .plan-save {
    width: 100%; margin-top: .5rem; border: none; background: var(--ink); color: var(--ground);
    border-radius: var(--radius); padding: .85rem; font-size: .95rem; font-family: inherit; cursor: pointer;
  }
  .plan-save:active { transform: scale(.99); }
  .plan-reset { margin-top: 1rem; text-align: center; }

  .exercise-row { margin: 0 0 1.5rem; padding-bottom: 1.3rem; border-bottom: 1px solid var(--line); }
  .exercise-row input[type="text"], .exercise-row select {
    display: block; width: 100%; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
    padding: .7rem .85rem; color: var(--ink); font-size: .9rem; font-family: inherit; margin-bottom: .5rem;
  }
  .exercise-row select { appearance: none; }
  .exercise-row label {
    display: inline-flex; align-items: center; gap: .4rem; font-size: .82rem; color: var(--ink-dim);
    margin: 0 1rem .6rem 0;
  }
  .exercise-save {
    display: block; width: 100%; margin-top: .3rem; border: none; background: var(--ink); color: var(--ground);
    border-radius: var(--radius); padding: .75rem; font-size: .9rem; font-family: inherit; cursor: pointer;
  }
  .exercise-save:active { transform: scale(.99); }
  .exercise-delete-form { margin-top: .5rem; text-align: right; }
  .exercise-add .plan-day { display: block; margin-bottom: .7rem; }

  .tabbar {
    position: fixed; left: 0; right: 0; bottom: 0; height: calc(var(--nav-h) + env(safe-area-inset-bottom, 0px));
    padding-bottom: env(safe-area-inset-bottom, 0px); background: rgba(14,15,17,.82); backdrop-filter: blur(14px);
    border-top: 1px solid var(--line); z-index: 10;
  }
  .tabbar-inner { max-width: 460px; margin: 0 auto; height: var(--nav-h); display: grid; grid-template-columns: repeat(5, 1fr); }
  .tab { background: none; border: none; cursor: pointer; color: var(--ink-mute); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: .25rem; font-family: inherit; font-size: .68rem; }
  .tab svg { width: 22px; height: 22px; stroke: currentColor; fill: none; stroke-width: 1.6; }
  .tab.active { color: var(--accent); }
  .tab:focus-visible { outline: 2px solid var(--accent); outline-offset: -4px; border-radius: 8px; }

  form.is-loading button[type="submit"] { opacity: .55; pointer-events: none; }
  form.is-loading button[type="submit"]::after {
    content: ""; display: inline-block; width: .7em; height: .7em; margin-left: .45em;
    vertical-align: -.05em; border: 2px solid currentColor; border-top-color: transparent;
    border-radius: 50%;
  }

  @media (prefers-reduced-motion: no-preference) {
    .view:not([hidden]) { animation: fade .28s ease; }
    @keyframes fade { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
    form.is-loading button[type="submit"]::after { animation: spin .7s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
  }
</style>
"""


def _t(value) -> str:
    """Escapt Textinhalt (nicht Attribute) — Apostrophe bleiben lesbar (z.B. Farmer's Walk)."""
    return html.escape(str(value), quote=False)


def _attr(value) -> str:
    """Escapt für Attributwerte in doppelten Anführungszeichen (z.B. input value=)."""
    return html.escape(str(value), quote=True)


def _num(value) -> str:
    """Deutsche Dezimaldarstellung mit Komma, ohne überflüssige Nullen."""
    return f"{value:g}".replace(".", ",")


def _entry_detail(entry: dict, session_only_exercises: set[str] | None = None) -> tuple[str, bool]:
    """Detail-Text + Flag, ob es ein 'absolviert'-Eintrag (grün) ist."""
    session_only_exercises = session_only_exercises if session_only_exercises is not None else SESSION_ONLY_EXERCISES
    if entry.get("type") == "bodyweight":
        return f"{_num(entry.get('weight_kg', 0))} kg", False

    exercise = entry.get("exercise")
    if entry.get("distance_km") is not None or entry.get("duration_min") is not None:
        parts = []
        if entry.get("distance_km") is not None:
            parts.append(f"{_num(entry['distance_km'])} km")
        if entry.get("duration_min") is not None:
            parts.append(f"{_num(entry['duration_min'])} min")
        return " · ".join(parts), False

    sets, reps, weight = entry.get("sets"), entry.get("reps"), entry.get("weight_kg")
    if exercise in session_only_exercises or (sets is None and reps is None and weight is None):
        return "✓ absolviert", True

    if sets is not None and reps is not None:
        base = f"{sets}×{reps}"
    elif reps is not None:
        base = f"{reps} Wdh."
    else:
        base = f"{sets} Sätze"
    if weight is not None:
        base += f" · {_num(weight)} kg"
    return base, False


def _entry_name(entry: dict) -> str:
    return "Körpergewicht" if entry.get("type") == "bodyweight" else entry.get("exercise", "?")


def _short_date(iso: str) -> str:
    d = date.fromisoformat(iso[:10])
    return f"{d.day:02d}. {MONTH_ABBR[d.month - 1]}"


def _chart_img(exercise: str, encoded_token: str, alt: str) -> str:
    src = f"/dashboard/chart.png?exercise={quote(exercise)}&token={encoded_token}"
    return f'<img class="chart" src="{src}" alt="{_t(alt)}" onerror="{_CHART_ONERROR}">'


def _hero_parts(plan: str) -> tuple[str, str]:
    """Zerlegt einen Plantext in Titel + Untertitel für den Heute-Hero."""
    if "(" in plan:
        title = plan.split("(", 1)[0].strip()
        sub = plan.split("(", 1)[1].replace("(", "").replace(")", "").strip()
        return title, sub
    if "–" in plan:
        title, sub = plan.split("–", 1)
        return title.strip(), sub.strip()
    return plan.strip(), ""


def _repeat_chips(last_sets: list[dict], session_only_exercises: set[str] | None = None) -> str:
    if not last_sets:
        return ""
    chips = []
    for entry in last_sets:
        detail, _ = _entry_detail(entry, session_only_exercises)
        label = f"{_entry_name(entry)} · {detail}"
        chips.append(
            f'<button type="button" class="chip" data-fill="{_attr(entry["raw_text"])}">{_t(label)}</button>'
        )
    return (
        '<div class="chips"><span class="micro-label">Zuletzt</span>'
        f'<div class="chip-row">{"".join(chips)}</div></div>'
    )


def _exercise_datalist(exercise_aliases: dict[str, list[str]]) -> str:
    options = "".join(f'<option value="{_attr(name)}">' for name in sorted(exercise_aliases))
    return f'<datalist id="exercise-names">{options}</datalist>'


# ---------------------------------------------------------------- Heute-View

def _heute_view(
    encoded_token: str,
    today: date | None,
    week_value: str,
    week_number: int | None,
    trained_dates: set[str],
    recent: list[dict],
    flash: str | None,
    plan_long: dict[int, str],
    plan_short: dict[int, str],
    active: bool,
    last_sets: list[dict] | None = None,
    exercise_aliases: dict[str, list[str]] | None = None,
    session_only_exercises: set[str] | None = None,
) -> str:
    exercise_aliases = exercise_aliases if exercise_aliases is not None else EXERCISE_ALIASES
    hidden_attr = "" if active else " hidden"
    parts = [f'<section class="view" id="view-heute"{hidden_attr}>']

    if today is not None:
        eyebrow = f"{WEEKDAY_FULL[today.weekday()]} · {today.day}. {MONTH_FULL[today.month - 1]}"
        pill = f'<div class="week-pill">{_t(week_value)}</div>' if week_number is not None else ""
        parts.append(
            f'<div class="today-head"><div class="eyebrow">{eyebrow}</div>{pill}</div>'
        )
        title, sub = _hero_parts(plan_long[today.weekday()])
        parts.append(f'<h1 class="hero">{_t(title)}</h1>')
        if sub:
            parts.append(f'<p class="hero-sub">{_t(sub)}</p>')

    if is_deload_week(week_number):
        parts.append(
            '<div class="note">📉 Deload-Woche (6–8): diese Woche ~60 % Gewicht, halbe Sätze einplanen.</div>'
        )

    parts.append(_repeat_chips(last_sets or [], session_only_exercises))

    parts.append(
        f'<form class="quick" method="post" data-ajax action="/dashboard/log?token={encoded_token}">'
        '<input type="text" name="text" required aria-label="Eintrag hinzufügen" '
        'list="exercise-names" '
        "placeholder='z. B. &quot;3×8 100 kg Kniebeuge&quot;'>"
        '<button type="submit" aria-label="Eintragen">→</button>'
        "</form>"
        f'<form class="undo-form" method="post" data-ajax action="/dashboard/undo?token={encoded_token}">'
        '<button type="submit" class="undo">↩ Letzten Eintrag rückgängig</button>'
        "</form>"
        f"{_exercise_datalist(exercise_aliases)}"
    )
    if flash:
        parts.append(f'<div class="flash">{_t(flash)}</div>')

    if today is not None:
        week_start = today - timedelta(days=today.weekday())
        cells = []
        for wd in range(7):
            day = week_start + timedelta(days=wd)
            is_today = day == today
            cls = "day today" if is_today else "day"
            mark = '<div class="dot"></div>' if is_today else (
                '<div class="d-mark">✓</div>' if day.isoformat() in trained_dates else '<div class="d-mark"></div>'
            )
            cells.append(
                f'<div class="{cls}"><div class="d-abbr">{WEEKDAY_ABBR[wd]}</div>'
                f'<div class="d-plan">{_t(plan_short[wd])}</div>{mark}</div>'
            )
        parts.append(f'<div class="week-strip">{"".join(cells)}</div>')

        todays = [e for e in recent if e.get("logged_at", "")[:10] == today.isoformat()]
        rows = []
        for e in todays:
            detail, done = _entry_detail(e, session_only_exercises)
            cls = "l-detail done" if done else "l-detail"
            rows.append(
                f'<div class="log-row"><span class="l-name">{_t(_entry_name(e))}</span>'
                f'<span class="{cls}">{_t(detail)}</span></div>'
            )
        body = "".join(rows) if rows else '<p class="empty-line">Heute noch nichts geloggt.</p>'
        parts.append(f'<div class="today-log"><span class="micro-label">Heute geloggt</span>{body}</div>')

    parts.append("</section>")
    return "".join(parts)


# ---------------------------------------------------------- Fortschritt-View

def _figure(value: str, unit: str, label: str) -> str:
    unit_html = f'<span class="f-unit"> {_t(unit)}</span>' if unit else ""
    return (
        f'<div class="figure"><div class="f-val">{_t(value)}{unit_html}</div>'
        f'<div class="f-label">{_t(label)}</div></div>'
    )


def _fortschritt_view(
    encoded_token: str,
    latest_weight: dict | None,
    training_days: int,
    week_value: str,
    summary: dict,
    active: bool,
    weight_delta: tuple[float, float] | None = None,
    plan_sections: list[tuple[str, list[str]]] | None = None,
    session_only_exercises: set[str] | None = None,
) -> str:
    plan_sections = plan_sections if plan_sections is not None else PLAN_SECTIONS
    weight_val = _num(latest_weight["weight_kg"]) if latest_weight else "–"
    hidden_attr = "" if active else " hidden"
    parts = [
        f'<section class="view" id="view-fortschritt"{hidden_attr}>',
        '<div class="view-head"><span class="micro-label">Überblick</span></div>',
        '<div class="figures">',
        _figure(weight_val, "kg" if latest_weight else "", "Gewicht"),
        _figure(week_value, "", "Woche"),
        _figure(str(training_days), "", "Trainingstage"),
        "</div>",
    ]

    parts.append('<div class="chart-block">')
    parts.append('<div class="chart-head"><h2>Körpergewicht</h2></div>')
    if latest_weight:
        parts.append(_chart_img("Gewicht", encoded_token, "Körpergewicht-Verlauf"))
        cap = f"Zielband {TARGET_WEIGHT_RANGE}"
        if weight_delta is not None:
            delta_text = format_weight_delta(*weight_delta).replace(".", ",")
            cap += f" · {delta_text} (7 Tage)"
        parts.append(f'<p class="chart-cap">{_t(cap)}</p>')
    else:
        parts.append('<p class="untracked-line">Noch keine Gewichtsdaten — schreib z. B. „Gewicht heute 84 kg".</p>')
    parts.append("</div>")

    covered: set[str] = set()
    for title, section_exercises in plan_sections:
        covered.update(section_exercises)
        parts.append(_section(title, section_exercises, summary, encoded_token, session_only_exercises))

    extra = sorted(set(summary) - covered)
    if extra:
        parts.append(_section("Sonstiges", extra, summary, encoded_token, session_only_exercises))

    parts.append("</section>")
    return "".join(parts)


def _section(
    title: str,
    exercises: list[str],
    summary: dict,
    encoded_token: str,
    session_only_exercises: set[str] | None = None,
) -> str:
    session_only_exercises = session_only_exercises if session_only_exercises is not None else SESSION_ONLY_EXERCISES
    tracked = [e for e in exercises if e in summary]
    untracked = [e for e in exercises if e not in summary]

    parts = [f'<span class="micro-label section-label">{_t(title)}</span>']
    cards = []
    for ex in tracked:
        if ex in session_only_exercises:
            info = summary[ex]
            cards.append(
                f'<div class="mini-card"><h3>{_t(ex)}</h3>'
                f'<p class="count-meta"><span class="count-num">{info["count"]}×</span> '
                f'· zuletzt {_short_date(info["last"])}</p></div>'
            )
        else:
            cards.append(
                f'<div class="mini-card"><h3>{_t(ex)}</h3>'
                f'{_chart_img(ex, encoded_token, ex + " Verlauf")}</div>'
            )
    if cards:
        parts.append(f'<div class="chart-grid">{"".join(cards)}</div>')
    if untracked:
        names = " · ".join(_t(e) for e in untracked)
        parts.append(f'<p class="untracked-line">Noch nicht getrackt: {names}</p>')
    return "".join(parts)


# ------------------------------------------------------------- Verlauf-View

def _entry_edit_panel(e: dict, encoded_token: str) -> str:
    """✎-Button + verstecktes Bearbeiten/Löschen-Panel für einen Verlauf-Eintrag."""
    entry_id = e.get("id")
    if entry_id is None:
        return ""
    kind = "bodyweight" if e.get("type") == "bodyweight" else "workout"
    target = f"entry-{kind}-{entry_id}"

    def val(key) -> str:
        v = e.get(key)
        return "" if v is None else (_num(v) if isinstance(v, float) else str(v))

    if kind == "bodyweight":
        fields = (
            '<label class="ef"><span>Gewicht (kg)</span>'
            f'<input name="weight_kg" value="{_attr(val("weight_kg"))}" inputmode="decimal" required></label>'
        )
    else:
        fields = (
            '<label class="ef ef-wide"><span>Übung</span>'
            f'<input name="exercise" value="{_attr(e.get("exercise", ""))}" list="exercise-names" required></label>'
            f'<label class="ef"><span>Sätze</span><input name="sets" value="{_attr(val("sets"))}" inputmode="numeric"></label>'
            f'<label class="ef"><span>Wdh.</span><input name="reps" value="{_attr(val("reps"))}" inputmode="numeric"></label>'
            f'<label class="ef"><span>Gewicht (kg)</span><input name="weight_kg" value="{_attr(val("weight_kg"))}" inputmode="decimal"></label>'
            f'<label class="ef"><span>Dauer (min)</span><input name="duration_min" value="{_attr(val("duration_min"))}" inputmode="decimal"></label>'
            f'<label class="ef"><span>Distanz (km)</span><input name="distance_km" value="{_attr(val("distance_km"))}" inputmode="decimal"></label>'
        )

    return (
        f'<button type="button" class="undo a-edit" data-edit-target="{target}" '
        'aria-label="Eintrag bearbeiten">✎</button>'
        f'<div class="entry-edit" id="{target}" hidden>'
        f'<form method="post" data-ajax action="/dashboard/entry/update?token={encoded_token}">'
        f'<input type="hidden" name="kind" value="{kind}">'
        f'<input type="hidden" name="id" value="{entry_id}">'
        f'<div class="entry-fields">{fields}</div>'
        '<button type="submit" class="exercise-save">Speichern</button>'
        "</form>"
        f'<form class="entry-delete" method="post" data-ajax data-confirm="Eintrag wirklich löschen?" '
        f'action="/dashboard/entry/delete?token={encoded_token}">'
        f'<input type="hidden" name="kind" value="{kind}">'
        f'<input type="hidden" name="id" value="{entry_id}">'
        '<button type="submit" class="undo">🗑 Löschen</button>'
        "</form></div>"
    )


def _verlauf_view(
    recent: list[dict],
    encoded_token: str,
    active: bool,
    session_only_exercises: set[str] | None = None,
) -> str:
    items = []
    for e in recent:
        detail, done = _entry_detail(e, session_only_exercises)
        cls = "a-detail done" if done else "a-detail"
        items.append(
            f'<li><span class="a-date">{_short_date(e["logged_at"])}</span>'
            f'<span class="a-name">{_t(_entry_name(e))}</span>'
            f'<span class="{cls}">{_t(detail)}</span>'
            f"{_entry_edit_panel(e, encoded_token)}</li>"
        )
    body = "".join(items) if items else '<p class="empty-line">Noch keine Einträge.</p>'
    hidden_attr = "" if active else " hidden"
    return (
        f'<section class="view" id="view-verlauf"{hidden_attr}>'
        '<div class="view-head"><span class="micro-label">Letzte Aktivitäten</span></div>'
        f'<ul class="activity">{body}</ul></section>'
    )


# ---------------------------------------------------------------- Plan-View

def _plan_view(encoded_token: str, plan_long: dict[int, str], plan_short: dict[int, str], active: bool) -> str:
    rows = []
    for wd in range(7):
        rows.append(
            f'<div class="plan-row"><span class="plan-day">{WEEKDAY_FULL[wd]}</span>'
            f'<input type="text" name="long_{wd}" value="{_attr(plan_long[wd])}" '
            f'aria-label="{WEEKDAY_FULL[wd]} Langform" required>'
            f'<input type="text" name="short_{wd}" value="{_attr(plan_short[wd])}" '
            f'aria-label="{WEEKDAY_FULL[wd]} Kurzform" placeholder="Kurzform für Wochenstreifen">'
            "</div>"
        )
    hidden_attr = "" if active else " hidden"
    return (
        f'<section class="view" id="view-plan"{hidden_attr}>'
        '<div class="view-head"><span class="micro-label">Wochenplan bearbeiten</span></div>'
        f'<form method="post" data-ajax action="/dashboard/plan?token={encoded_token}">'
        f'{"".join(rows)}'
        '<button type="submit" class="plan-save">Speichern</button>'
        "</form>"
        f'<div class="plan-reset"><form method="post" data-ajax action="/dashboard/plan/reset?token={encoded_token}" class="undo-form">'
        '<button type="submit" class="undo">↺ Auf Standard zurücksetzen</button>'
        "</form></div>"
        "</section>"
    )


# ------------------------------------------------------------- Übungen-View

def _section_select(name_attr: str, selected: str) -> str:
    options = ['<option value="">— keine —</option>']
    for title in _SECTION_TITLES:
        sel = " selected" if title == selected else ""
        options.append(f'<option value="{_attr(title)}"{sel}>{_t(title)}</option>')
    return f'<select name="{name_attr}" aria-label="Tag">{"".join(options)}</select>'


def _uebungen_view(
    encoded_token: str,
    exercise_aliases: dict[str, list[str]],
    cardio_exercises: set[str],
    session_only_exercises: set[str],
    plan_sections: list[tuple[str, list[str]]],
    active: bool,
) -> str:
    section_by_name: dict[str, str] = {}
    for title, names in plan_sections:
        for name in names:
            section_by_name[name] = title

    rows = []
    for name in sorted(exercise_aliases):
        aliases_text = ", ".join(exercise_aliases[name])
        cardio_checked = " checked" if name in cardio_exercises else ""
        session_checked = " checked" if name in session_only_exercises else ""
        rows.append(
            '<div class="exercise-row">'
            f'<form method="post" data-ajax action="/dashboard/exercises/update?token={encoded_token}">'
            f'<input type="hidden" name="original_name" value="{_attr(name)}">'
            f'<input type="text" name="name" value="{_attr(name)}" aria-label="Name" required>'
            f'<input type="text" name="aliases" value="{_attr(aliases_text)}" '
            'aria-label="Aliase (kommagetrennt)" placeholder="Aliase, kommagetrennt">'
            f'{_section_select("section", section_by_name.get(name, ""))}'
            f'<label><input type="checkbox" name="is_cardio"{cardio_checked}> Cardio</label>'
            f'<label><input type="checkbox" name="is_session_only"{session_checked}> Ohne Zahlen (Session)</label>'
            '<button type="submit" class="exercise-save">Speichern</button>'
            "</form>"
            f'<div class="exercise-delete-form"><form method="post" data-ajax '
            f'action="/dashboard/exercises/delete?token={encoded_token}">'
            f'<input type="hidden" name="name" value="{_attr(name)}">'
            '<button type="submit" class="undo">🗑 Löschen</button>'
            "</form></div>"
            "</div>"
        )

    add_form = (
        '<div class="exercise-row exercise-add"><span class="plan-day">Neue Übung</span>'
        f'<form method="post" data-ajax action="/dashboard/exercises/add?token={encoded_token}">'
        '<input type="text" name="name" aria-label="Name" placeholder="Name" required>'
        '<input type="text" name="aliases" aria-label="Aliase (kommagetrennt)" '
        'placeholder="Aliase, kommagetrennt (optional)">'
        f'{_section_select("section", "")}'
        '<label><input type="checkbox" name="is_cardio"> Cardio</label>'
        '<label><input type="checkbox" name="is_session_only"> Ohne Zahlen (Session)</label>'
        '<button type="submit" class="exercise-save">Hinzufügen</button>'
        "</form></div>"
    )

    hidden_attr = "" if active else " hidden"
    return (
        f'<section class="view" id="view-uebungen"{hidden_attr}>'
        '<div class="view-head"><span class="micro-label">Übungen verwalten</span></div>'
        f'{"".join(rows)}{add_form}'
        "</section>"
    )


_TABS = [
    (
        "heute", "Heute",
        '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/>',
    ),
    ("fortschritt", "Fortschritt", '<path d="M4 19V5M4 19h16M8 15l3.5-4 3 2.5L20 8"/>'),
    ("verlauf", "Verlauf", '<path d="M4 6h16M4 12h16M4 18h10"/>'),
    ("plan", "Plan", '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>'),
    ("uebungen", "Übungen", '<rect x="2" y="10" width="3" height="4" rx="1"/><rect x="19" y="10" width="3" height="4" rx="1"/><path d="M5 12h14"/>'),
]


def _tabbar(view: str) -> str:
    buttons = []
    for key, label, icon in _TABS:
        cls = "tab active" if key == view else "tab"
        buttons.append(f'<button class="{cls}" data-view="{key}"><svg viewBox="0 0 24 24">{icon}</svg>{label}</button>')
    return f'<nav class="tabbar"><div class="tabbar-inner">{"".join(buttons)}</div></nav>'


_SCRIPT = """
<script>
  var views = {
    heute: "view-heute", fortschritt: "view-fortschritt", verlauf: "view-verlauf",
    plan: "view-plan", uebungen: "view-uebungen"
  };
  var currentView = "heute";

  function activateView(v) {
    document.querySelectorAll(".tab").forEach(function (x) { x.classList.toggle("active", x.dataset.view === v); });
    Object.keys(views).forEach(function (k) { document.getElementById(views[k]).hidden = (k !== v); });
  }

  // Nach jedem AJAX-Swap erneut aufgerufen: per innerHTML/replaceWith eingesetzte
  // Elemente haben keine Listener mehr.
  function initDashboard() {
    document.querySelectorAll(".tab").forEach(function (t) {
      t.addEventListener("click", function () {
        currentView = t.dataset.view;
        activateView(currentView);
        window.scrollTo(0, 0);
      });
    });
    document.querySelectorAll(".chip").forEach(function (c) {
      c.addEventListener("click", function () {
        var input = document.querySelector(".quick input");
        input.value = c.dataset.fill;
        input.focus();
      });
    });
    document.querySelectorAll("[data-edit-target]").forEach(function (b) {
      b.addEventListener("click", function () {
        var panel = document.getElementById(b.dataset.editTarget);
        if (panel) panel.hidden = !panel.hidden;
      });
    });
  }

  function showAjaxError(form) {
    var flash = document.createElement("div");
    flash.className = "flash";
    flash.textContent = "\\u26a0\\ufe0f Netzwerkfehler \\u2014 bitte nochmal versuchen.";
    form.insertAdjacentElement("afterend", flash);
    setTimeout(function () { flash.remove(); }, 5000);
  }

  document.addEventListener("submit", function (ev) {
    var form = ev.target;
    if (!form.matches("[data-ajax]")) return;
    ev.preventDefault();
    if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) return;

    var wasQuick = form.classList.contains("quick");
    var btn = form.querySelector('button[type="submit"]');
    form.classList.add("is-loading");
    form.setAttribute("aria-busy", "true");
    if (btn) btn.disabled = true;

    fetch(form.action, { method: "POST", body: new FormData(form) })
      .then(function (resp) {
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        return resp.text();
      })
      .then(function (htmlText) {
        var next = new DOMParser().parseFromString(htmlText, "text/html").querySelector(".app");
        var current = document.querySelector(".app");
        if (!next || !current) { window.location.reload(); return; }
        current.replaceWith(next);
        initDashboard();
        activateView(currentView);
        if (wasQuick) {
          var input = document.querySelector(".quick input");
          if (input) input.focus();
        }
      })
      .catch(function () {
        form.classList.remove("is-loading");
        form.removeAttribute("aria-busy");
        if (btn) btn.disabled = false;
        showAjaxError(form);
      });
  });

  var activeTab = document.querySelector(".tab.active");
  if (activeTab) { currentView = activeTab.dataset.view; }
  initDashboard();
  if ("serviceWorker" in navigator) { navigator.serviceWorker.register("/sw.js"); }
</script>
"""


_VIEWS = {"heute", "fortschritt", "verlauf", "plan", "uebungen"}


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
    plan_long: dict[int, str] | None = None,
    plan_short: dict[int, str] | None = None,
    view: str = "heute",
    weight_delta: tuple[float, float] | None = None,
    last_sets: list[dict] | None = None,
    exercise_aliases: dict[str, list[str]] | None = None,
    cardio_exercises: set[str] | None = None,
    session_only_exercises: set[str] | None = None,
    plan_sections: list[tuple[str, list[str]]] | None = None,
) -> str:
    encoded_token = quote(token)
    summary = exercise_summary or {}
    plan_long = plan_long if plan_long is not None else TRAINING_PLAN
    plan_short = plan_short if plan_short is not None else TRAINING_PLAN_SHORT
    exercise_aliases = exercise_aliases if exercise_aliases is not None else EXERCISE_ALIASES
    cardio_exercises = cardio_exercises if cardio_exercises is not None else CARDIO_EXERCISES
    session_only_exercises = session_only_exercises if session_only_exercises is not None else SESSION_ONLY_EXERCISES
    plan_sections = plan_sections if plan_sections is not None else PLAN_SECTIONS
    view = view if view in _VIEWS else "heute"

    if week_number is None:
        week_value = "–"
    elif week_number <= PROGRAM_LENGTH_WEEKS:
        week_value = f"{week_number} / {PROGRAM_LENGTH_WEEKS}"
    else:
        week_value = "fertig"

    heute = _heute_view(
        encoded_token, today, week_value, week_number, trained_dates or set(), recent, flash,
        plan_long, plan_short, view == "heute", last_sets, exercise_aliases, session_only_exercises,
    )
    fortschritt = _fortschritt_view(
        encoded_token, latest_weight, training_days, week_value, summary, view == "fortschritt",
        weight_delta, plan_sections, session_only_exercises,
    )
    verlauf = _verlauf_view(recent, encoded_token, view == "verlauf", session_only_exercises)
    plan = _plan_view(encoded_token, plan_long, plan_short, view == "plan")
    uebungen = _uebungen_view(
        encoded_token, exercise_aliases, cardio_exercises, session_only_exercises, plan_sections,
        view == "uebungen",
    )

    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Trainings-Tracker</title>
  <link rel="manifest" href="/manifest.webmanifest?token={encoded_token}">
  <link rel="apple-touch-icon" href="/static/icon-192.png">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="theme-color" content="#0e0f11">
  {_STYLE}
</head>
<body>
  <div class="app">
    {heute}
    {fortschritt}
    {verlauf}
    {plan}
    {uebungen}
    {_tabbar(view)}
  </div>
  {_SCRIPT}
</body>
</html>"""
