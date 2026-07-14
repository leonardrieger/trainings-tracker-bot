"""Helper für den Telegram Bot API (sendMessage / sendPhoto / Datei-Download)."""
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


def get_file_bytes(file_id: str) -> bytes:
    """Lädt eine von Telegram gehostete Datei (z.B. eine Sprachnachricht) herunter."""
    meta_response = httpx.get(f"{_base_url()}/getFile", params={"file_id": file_id}, timeout=10)
    meta_response.raise_for_status()
    file_path = meta_response.json()["result"]["file_path"]

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    file_response = httpx.get(f"https://api.telegram.org/file/bot{token}/{file_path}", timeout=20)
    file_response.raise_for_status()
    return file_response.content
