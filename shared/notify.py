"""Centralized Telegram notification sender.

Usage:
    from shared.notify import send_telegram
    send_telegram("Text message")
    send_telegram("<b>HTML</b> message", parse_mode="HTML")
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

_enabled = bool(BOT_TOKEN) and bool(CHAT_ID)


def send_telegram(
    text: str,
    parse_mode: str = "Markdown",
    chat_id: str | None = None,
) -> bool:
    if not _enabled:
        logger.debug("Telegram disabled — token or chat_id not set")
        return False

    target = chat_id or CHAT_ID
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = httpx.post(
            url,
            json={"chat_id": target, "text": text, "parse_mode": parse_mode},
            timeout=15,
        )
        data = resp.json()
        if not data.get("ok"):
            logger.warning(
                "Telegram API error (HTTP %d): %s",
                resp.status_code,
                data.get("description", "unknown"),
            )
            return False
        return True
    except Exception as e:
        logger.warning("Telegram send failed: %s", e)
        return False
