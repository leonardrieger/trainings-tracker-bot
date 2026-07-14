"""Helper für den Telegram Bot API (sendMessage / sendPhoto)."""
from __future__ import annotations

import io
import os

import httpx


def _base_url() -> str:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    return f"https://api.telegram.org/bot{token}"


def send_message(chat_id: int, text: str) -> None:
    httpx.post(f"{_base_url()}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)


def send_photo(chat_id: int, image_bytes: bytes, caption: str | None = None) -> None:
    files = {"photo": ("chart.png", io.BytesIO(image_bytes), "image/png")}
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
    httpx.post(f"{_base_url()}/sendPhoto", data=data, files=files, timeout=20)
