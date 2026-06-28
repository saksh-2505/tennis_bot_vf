"""Telegram notification utility for the app container.

Reads bot token and chat ID from environment variables.
Uses httpx (already a project dependency) for HTTP calls.
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

_enabled = bool(BOT_TOKEN and CHAT_ID)


def send_message(text: str) -> bool:
    if not _enabled:
        logger.debug("Telegram disabled — set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        return False
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=15,
        )
        return resp.is_success
    except Exception as e:
        logger.warning("Telegram send failed: %s", e)
        return False
