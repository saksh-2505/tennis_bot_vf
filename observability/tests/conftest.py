import sys
from unittest.mock import MagicMock

mock_db = MagicMock()
mock_db.SessionLocal = MagicMock()
mock_db.engine = MagicMock()
mock_db.Base = MagicMock()
mock_db.check_connection = MagicMock(return_value=True)
mock_db.init_db = MagicMock()
sys.modules["database"] = mock_db

from observability.metrics import get_metrics


def pytest_configure(config):
    get_metrics().reset()


def pytest_unconfigure(config):
    get_metrics().reset()
