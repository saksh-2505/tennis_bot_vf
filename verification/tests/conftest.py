"""Verification tests conftest."""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

mock_db = MagicMock()
mock_session = MagicMock()
mock_session.execute.return_value.scalar.return_value = 0
mock_session.execute.return_value.fetchall.return_value = []
mock_session.execute.return_value.fetchone.return_value = None
mock_session.execute.return_value.scalar_one_or_none.return_value = None

mock_session_local = MagicMock()
mock_session_local.return_value.__enter__.return_value = mock_session

mock_db.SessionLocal = mock_session_local
mock_db.engine = MagicMock()
mock_db.Base = MagicMock()
mock_db.check_connection = MagicMock(return_value=True)
mock_db.init_db = MagicMock()
mock_db.get_db = MagicMock()
sys.modules["database"] = mock_db

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")
os.environ.setdefault("TELEGRAM_CHAT_ID", "")
