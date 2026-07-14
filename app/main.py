"""FastAPI-App: Telegram-Webhook-Endpoint + Command-Routing."""
from __future__ import annotations

import os

from fastapi import FastAPI, Request

from app import db, telegram
from app.chart import render_progress_chart
from app.llm_parser import parse_message

app = FastAPI()


def _allowed_user_id() -> int:
    return int(os.environ["ALLOWED_TELEGRAM_USER_ID"])


@app.get("/")
def health() -> dict:
    return {"status": "ok"}


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
        entries = db.get_history(user_id, exercise, limit=100)
        image = render_progress_chart(exercise, entries)
        if image is None:
            telegram.send_message(chat_id, f"Keine ausreichenden Daten für '{exercise}'.")
        else:
            telegram.send_photo(chat_id, image, caption=f"Fortschritt: {exercise}")
        return {"ok": True}

    parsed = parse_message(text)
    db.insert_log(user_id, parsed)
    telegram.send_message(chat_id, parsed.confirmation_text())
    return {"ok": True}
