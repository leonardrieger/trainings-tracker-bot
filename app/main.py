"""FastAPI-App: Telegram-Webhook-Endpoint + Command-Routing."""
from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse

from app import db, telegram
from app.chart import render_progress_chart
from app.dashboard import render_dashboard_html
from app.llm_parser import parse_message
from app.reminders import reminder_text, should_send_reminder

app = FastAPI()

BODYWEIGHT_ALIASES = {"gewicht", "körpergewicht", "koerpergewicht"}
BERLIN = ZoneInfo("Europe/Berlin")


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
    und verschickt bei Bedarf die morgendliche Trainings-Erinnerung."""
    if token != os.environ.get("CRON_SECRET"):
        return {"ok": False}

    now = datetime.now(BERLIN)
    last_sent = db.get_last_reminder_date()
    if should_send_reminder(now, last_sent):
        telegram.send_message(_allowed_user_id(), reminder_text(now.date()))
        db.set_last_reminder_date(now.date())
        return {"ok": True, "reminder_sent": True}
    return {"ok": True, "reminder_sent": False}


@app.post("/webhook")
async def webhook(request: Request) -> dict:
    update = await request.json()
    message = update.get("message")
    if not message or "text" not in message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message["text"].strip()

    if user_id != _allowed_user_id():
        return {"ok": True}

    if text == "/start":
        telegram.send_message(
            chat_id,
            "👋 Trainings-Tracker bereit. Schick mir z.B.\n"
            '"2 Sätze 8 Wiederholungen 80kg Bankdrücken"\n\n'
            f"Deine Telegram-User-ID: {user_id}\n"
            "Befehle: /verlauf <übung>, /chart <übung>",
        )
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
            date = e["logged_at"][:10]
            if e.get("distance_km") is not None or e.get("duration_min") is not None:
                lines.append(f"{date}: {e.get('distance_km', '-')}km / {e.get('duration_min', '-')}min")
            else:
                lines.append(f"{date}: {e.get('sets', '-')}x{e.get('reps', '-')} @ {e.get('weight_kg', '-')}kg")
        telegram.send_message(chat_id, "\n".join(lines))
        return {"ok": True}

    if text.startswith("/chart"):
        exercise = text.removeprefix("/chart").strip()
        if not exercise:
            telegram.send_message(chat_id, "Nutzung: /chart <übung>")
            return {"ok": True}
        if exercise.lower() in BODYWEIGHT_ALIASES:
            entries = db.get_body_weight_history(user_id, limit=200)
            image = render_progress_chart("Körpergewicht", entries)
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
    if parsed.record_type == "bodyweight":
        if parsed.weight_kg is not None:
            db.insert_body_weight(user_id, parsed.weight_kg, parsed.raw_text)
        telegram.send_message(chat_id, parsed.confirmation_text())
        return {"ok": True}

    db.insert_log(user_id, parsed)
    telegram.send_message(chat_id, parsed.confirmation_text())
    return {"ok": True}


@app.get("/dashboard")
def dashboard(token: str = "") -> HTMLResponse:
    if not _dashboard_authorized(token):
        return HTMLResponse("Unauthorized", status_code=401)
    user_id = _allowed_user_id()
    exercises = db.list_exercises(user_id)
    recent = db.get_recent_activity(user_id, limit=20)
    return HTMLResponse(render_dashboard_html(exercises, recent, token))


@app.get("/dashboard/chart.png")
def dashboard_chart(exercise: str, token: str = "") -> Response:
    if not _dashboard_authorized(token):
        return Response(status_code=401)
    user_id = _allowed_user_id()
    if exercise.lower() in BODYWEIGHT_ALIASES:
        entries = db.get_body_weight_history(user_id, limit=200)
        label = "Körpergewicht"
    else:
        entries = db.get_history(user_id, exercise, limit=200)
        label = exercise
    image = render_progress_chart(label, entries)
    if image is None:
        return Response(status_code=404)
    return Response(content=image, media_type="image/png")
