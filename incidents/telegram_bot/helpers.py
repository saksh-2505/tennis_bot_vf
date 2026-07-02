"""Helpers for Telegram bot: reply sending, HTML escaping."""

import html
import logging

from shared.notify import send_telegram

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
    ok = send_telegram(text, parse_mode="HTML", chat_id=str(chat_id))
    if not ok:
        raise RuntimeError("Telegram API error: send failed")
