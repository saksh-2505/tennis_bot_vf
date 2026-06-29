"""Helpers for Telegram bot: reply sending, HTML escaping."""

import html
import logging

import httpx

from incidents.telegram_bot.offset_store import OFFSET_FILE

logger = logging.getLogger(__name__)

BOT_TOKEN: str = ""
_enabled: bool = False
_MAX_REPLY_LENGTH = 3800
_MAX_RESULTS = 15

_e = html.escape


def init_bot(token: str) -> None:
    global BOT_TOKEN, _enabled
    BOT_TOKEN = token
    _enabled = bool(token)


def is_enabled() -> bool:
    return _enabled


def max_results() -> int:
    return _MAX_RESULTS


def send_reply(chat_id: int, text: str) -> None:
    if not _enabled:
        return
    if len(text) > _MAX_REPLY_LENGTH:
        text = text[:_MAX_REPLY_LENGTH] + "\n\n\u2026 (truncated)"
    resp = httpx.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    data = resp.json()
    if not data.get("ok"):
        err_desc = data.get("description", "unknown error")
        logger.error("Telegram API error (HTTP %d): %s", resp.status_code, err_desc)
        raise RuntimeError(f"Telegram API error: {err_desc}")
