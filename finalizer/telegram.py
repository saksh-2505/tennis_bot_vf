"""Telegram notification utility for the app container.

Delegates to shared/notify.py for actual HTTP calls.
"""

import logging

from shared.notify import send_telegram

logger = logging.getLogger(__name__)


def send_message(text: str) -> bool:
    return send_telegram(text, parse_mode="HTML")
