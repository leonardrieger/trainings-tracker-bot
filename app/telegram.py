"""Helper für den Telegram Bot API (sendMessage / sendPhoto)."""
from __future__ import annotations

import io
import os

import httpx


def _base_url() -> str:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    return f"https://api.telegram.org/bot{token}"


def send_message(chat_id: int, text: str, reply_markup: dict | None = None) -> None:
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    httpx.post(f"{_base_url()}/sendMessage", json=payload, timeout=10)


def answer_callback_query(callback_query_id: str, text: str | None = None) -> None:
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    httpx.post(f"{_base_url()}/answerCallbackQuery", json=payload, timeout=10)


def send_photo(chat_id: int, image_bytes: bytes, caption: str | None = None) -> None:
    files = {"photo": ("chart.png", io.BytesIO(image_bytes), "image/png")}
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
    httpx.post(f"{_base_url()}/sendPhoto", data=data, files=files, timeout=20)
