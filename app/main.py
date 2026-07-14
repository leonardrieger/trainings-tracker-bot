"""FastAPI-App: Telegram-Webhook-Endpoint + Command-Routing."""
from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import chat, db, telegram
from app.chart import render_progress_chart
from app.dashboard import render_dashboard_html
from app.llm_parser import parse_message
from app.reminders import (
    reminder_text,
    should_send_reminder,
    should_send_weekly_summary,
    week_number_for,
    weekly_summary_text,
)

app = FastAPI()
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

BODYWEIGHT_ALIASES = {"gewicht", "körpergewicht", "koerpergewicht"}
BODYWEIGHT_TARGET_RANGE = (87.0, 89.0)
BERLIN = ZoneInfo("Europe/Berlin")

_SERVICE_WORKER_JS = """\
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});
"""


def _allowed_user_id() -> int:
    return int(os.environ["ALLOWED_TELEGRAM_USER_ID"])


def _dashboard_authorized(token: str) -> bool:
    expected = os.environ.get("DASHBOARD_TOKEN")
    return bool(expected) and token == expected


@app.get("/")
def health() -> dict:
    return {"status": "ok"}


@app.get("/cron/tick")
def cron_tick(token: str = "") -> dict:
    """Von einem externen Ping-Dienst alle ~10 Minuten aufgerufen: hält Render wach
    und verschickt bei Bedarf die morgendliche Trainings-Erinnerung sowie sonntags
    den Wochenrückblick."""
    if token != os.environ.get("CRON_SECRET"):
        return {"ok": False}

    now = datetime.now(BERLIN)
    user_id = _allowed_user_id()
    result = {"ok": True, "reminder_sent": False, "weekly_summary_sent": False}

    last_sent = db.get_last_reminder_date()
    if should_send_reminder(now, last_sent):
        start_date = db.get_program_start_date()
        week_number = week_number_for(now.date(), start_date)
        telegram.send_message(user_id, reminder_text(now.date(), week_number))
        db.set_last_reminder_date(now.date())
        result["reminder_sent"] = True

    last_weekly = db.get_last_weekly_summary_date()
    if should_send_weekly_summary(now, last_weekly):
        week_start = now.date() - timedelta(days=now.date().weekday())
        week_end = week_start + timedelta(days=6)
        training_days = db.get_workout_days_in_range(user_id, week_start, week_end)
        weight_change = db.get_weight_change_in_range(user_id, week_start, week_end)
        telegram.send_message(user_id, weekly_summary_text(training_days, weight_change))
        db.set_last_weekly_summary_date(now.date())
        result["weekly_summary_sent"] = True

    return result


@app.post("/webhook")
async def webhook(request: Request) -> dict:
    # Nur Telegram kennt das beim setWebhook hinterlegte Secret - gefälschte
    # POSTs von Dritten (erratene URL, gespoofte from.id) fallen hier durch.
    expected_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    if expected_secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != expected_secret:
        return {"ok": True}

    update = await request.json()
    message = update.get("message")
    if not message or "text" not in message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message["text"].strip()

    if user_id != _allowed_user_id():
        return {"ok": True}

    try:
        return _handle_message(chat_id, user_id, text)
    except Exception:
        logging.exception("Fehler bei Verarbeitung der Nachricht: %r", text)
        try:
            telegram.send_message(
                chat_id,
                "⚠️ Da ist gerade etwas schiefgelaufen — der Eintrag wurde "
                "möglicherweise nicht gespeichert. Probier es gleich nochmal.",
            )
        except Exception:
            pass
        return {"ok": True}


def _undo_message(deleted: dict | None) -> str:
    if deleted is None:
        return "Nichts zum Löschen gefunden."
    if deleted["type"] == "bodyweight":
        desc = f"Körpergewicht {deleted.get('weight_kg', '-')}kg vom {deleted['logged_at'][:10]}"
    else:
        desc = f"{deleted.get('exercise', '?')} vom {deleted['logged_at'][:10]}"
    return f"🗑️ Gelöscht: {desc}"


def _handle_message(chat_id: int, user_id: int, text: str) -> dict:
    if text == "/start":
        telegram.send_message(
            chat_id,
            "👋 Trainings-Tracker bereit. Schick mir z.B.\n"
            '"2 Sätze 8 Wiederholungen 80kg Bankdrücken"\n\n'
            f"Deine Telegram-User-ID: {user_id}\n"
            "Befehle: /verlauf <übung>, /chart <übung>, /programm [datum], /undo",
        )
        return {"ok": True}

    if text == "/undo":
        deleted = db.delete_last_entry(user_id)
        telegram.send_message(chat_id, _undo_message(deleted))
        return {"ok": True}

    if text.startswith("/programm"):
        arg = text.removeprefix("/programm").strip()
        if arg:
            try:
                start_date = date.fromisoformat(arg)
            except ValueError:
                telegram.send_message(chat_id, "Format: /programm JJJJ-MM-TT, z.B. /programm 2026-07-14")
                return {"ok": True}
            db.set_program_start_date(start_date)
            week_number = week_number_for(datetime.now(BERLIN).date(), start_date)
            telegram.send_message(
                chat_id, f"✅ Programmstart gesetzt: {start_date.isoformat()} (Woche {week_number}/12)"
            )
            return {"ok": True}

        start_date = db.get_program_start_date()
        if start_date is None:
            telegram.send_message(chat_id, "Noch kein Startdatum gesetzt. Nutzung: /programm 2026-07-14")
            return {"ok": True}
        week_number = week_number_for(datetime.now(BERLIN).date(), start_date)
        status = f"Woche {week_number}/12" if week_number and week_number <= 12 else "Programm abgeschlossen 🎉"
        telegram.send_message(chat_id, f"Start: {start_date.isoformat()} — {status}")
        return {"ok": True}

    if text.startswith("/verlauf"):
        exercise = text.removeprefix("/verlauf").strip()
        if not exercise:
            telegram.send_message(chat_id, "Nutzung: /verlauf <übung>")
            return {"ok": True}
        if exercise.lower() in BODYWEIGHT_ALIASES:
            entries = db.get_body_weight_history(user_id)
            if not entries:
                telegram.send_message(chat_id, "Keine Körpergewicht-Einträge gefunden.")
                return {"ok": True}
            lines = ["Verlauf für Körpergewicht:"]
            for e in entries:
                lines.append(f"{e['logged_at'][:10]}: {e.get('weight_kg', '-')}kg")
            telegram.send_message(chat_id, "\n".join(lines))
            return {"ok": True}
        entries = db.get_history(user_id, exercise)
        if not entries:
            telegram.send_message(chat_id, f"Keine Einträge für '{exercise}' gefunden.")
            return {"ok": True}
        lines = [f"Verlauf für {exercise}:"]
        for e in entries:
            entry_date = e["logged_at"][:10]
            if e.get("distance_km") is not None or e.get("duration_min") is not None:
                lines.append(f"{entry_date}: {e.get('distance_km', '-')}km / {e.get('duration_min', '-')}min")
            else:
                lines.append(f"{entry_date}: {e.get('sets', '-')}x{e.get('reps', '-')} @ {e.get('weight_kg', '-')}kg")
        telegram.send_message(chat_id, "\n".join(lines))
        return {"ok": True}

    if text.startswith("/chart"):
        exercise = text.removeprefix("/chart").strip()
        if not exercise:
            telegram.send_message(chat_id, "Nutzung: /chart <übung>")
            return {"ok": True}
        if exercise.lower() in BODYWEIGHT_ALIASES:
            entries = db.get_body_weight_history(user_id, limit=200)
            image = render_progress_chart("Körpergewicht", entries, target_range=BODYWEIGHT_TARGET_RANGE)
            if image is None:
                telegram.send_message(chat_id, "Keine ausreichenden Daten für Körpergewicht.")
            else:
                telegram.send_photo(chat_id, image, caption="Fortschritt: Körpergewicht")
            return {"ok": True}
        entries = db.get_history(user_id, exercise, limit=100)
        image = render_progress_chart(exercise, entries)
        if image is None:
            telegram.send_message(chat_id, f"Keine ausreichenden Daten für '{exercise}'.")
        else:
            telegram.send_photo(chat_id, image, caption=f"Fortschritt: {exercise}")
        return {"ok": True}

    parsed = parse_message(text)
    if parsed.recognized:
        if parsed.record_type == "bodyweight":
            db.insert_body_weight(user_id, parsed.weight_kg, parsed.raw_text)
        else:
            db.insert_log(user_id, parsed)
        telegram.send_message(chat_id, parsed.confirmation_text())
        return {"ok": True}

    # Kein Log-Eintrag erkannt -> als freie Frage an den Chat weiterreichen,
    # statt sie als Datenmüll ("Unbekannt") zu speichern.
    today = datetime.now(BERLIN).date()
    week_number = week_number_for(today, db.get_program_start_date())
    telegram.send_message(chat_id, chat.answer_question(user_id, text, today, week_number))
    return {"ok": True}


@app.get("/dashboard")
def dashboard(token: str = "", msg: str = "") -> HTMLResponse:
    if not _dashboard_authorized(token):
        return HTMLResponse("Unauthorized", status_code=401)
    user_id = _allowed_user_id()
    summary = db.get_exercise_summary(user_id)
    recent = db.get_recent_activity(user_id, limit=20)
    latest_weight_history = db.get_body_weight_history(user_id, limit=1)
    latest_weight = latest_weight_history[0] if latest_weight_history else None
    training_days = db.get_training_days_count(user_id)
    start_date = db.get_program_start_date()
    today = datetime.now(BERLIN).date()
    week_number = week_number_for(today, start_date)
    week_start = today - timedelta(days=today.weekday())
    trained_dates = db.get_workout_dates_in_range(user_id, week_start, week_start + timedelta(days=6))
    html = render_dashboard_html(
        recent, token, latest_weight, training_days, summary, week_number, today, trained_dates,
        flash=msg or None,
    )
    return HTMLResponse(html)


@app.get("/dashboard/chart.png")
def dashboard_chart(exercise: str, token: str = "") -> Response:
    if not _dashboard_authorized(token):
        return Response(status_code=401)
    user_id = _allowed_user_id()
    if exercise.lower() in BODYWEIGHT_ALIASES:
        entries = db.get_body_weight_history(user_id, limit=200)
        image = render_progress_chart("Körpergewicht", entries, target_range=BODYWEIGHT_TARGET_RANGE)
    else:
        entries = db.get_history(user_id, exercise, limit=200)
        image = render_progress_chart(exercise, entries)
    if image is None:
        return Response(status_code=404)
    return Response(content=image, media_type="image/png")


@app.post("/dashboard/log")
def dashboard_log(text: str = Form(...), token: str = "") -> Response:
    if not _dashboard_authorized(token):
        return Response(status_code=401)
    user_id = _allowed_user_id()
    parsed = parse_message(text)
    if parsed.recognized:
        if parsed.record_type == "bodyweight":
            db.insert_body_weight(user_id, parsed.weight_kg, parsed.raw_text)
        else:
            db.insert_log(user_id, parsed)
        msg = parsed.confirmation_text()
    else:
        msg = f'⚠️ Nicht erkannt: "{text}". Versuch\'s z.B. mit "3x8 100kg Kniebeuge".'
    return RedirectResponse(f"/dashboard?token={quote(token)}&msg={quote(msg)}", status_code=303)


@app.post("/dashboard/undo")
def dashboard_undo(token: str = "") -> Response:
    if not _dashboard_authorized(token):
        return Response(status_code=401)
    deleted = db.delete_last_entry(_allowed_user_id())
    msg = _undo_message(deleted)
    return RedirectResponse(f"/dashboard?token={quote(token)}&msg={quote(msg)}", status_code=303)


@app.get("/sw.js")
def service_worker() -> Response:
    return Response(content=_SERVICE_WORKER_JS, media_type="application/javascript")


@app.get("/manifest.webmanifest")
def manifest(token: str = "") -> Response:
    if not _dashboard_authorized(token):
        return Response(status_code=401)
    data = {
        "name": "Trainings-Tracker",
        "short_name": "Training",
        "start_url": f"/dashboard?token={quote(token)}",
        "scope": "/",
        "display": "standalone",
        "background_color": "#0e0f11",
        "theme_color": "#0e0f11",
        "icons": [
            {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }
    return Response(content=json.dumps(data), media_type="application/manifest+json")
