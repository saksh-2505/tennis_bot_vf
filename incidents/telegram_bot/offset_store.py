"""Offset file persistence for Telegram bot updates."""

import logging

OFFSET_FILE = "/tmp/telegram_offset"

logger = logging.getLogger(__name__)


def read_offset() -> int:
    try:
        with open(OFFSET_FILE) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError, OSError):
        return 0


def write_offset(offset: int) -> None:
    try:
        with open(OFFSET_FILE, "w") as f:
            f.write(str(offset))
    except OSError:
        pass
