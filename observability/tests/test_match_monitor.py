from unittest.mock import patch, MagicMock

import pytest

from observability.match_monitor import get_match_monitor, MatchMonitor


class TestMatchMonitor:
    def setup_method(self):
        self.monitor = MatchMonitor()

    def test_empty_monitor(self):
        assert self.monitor.get_all_match_health() == {}

    def test_get_nonexistent_match(self):
        assert self.monitor.get_match_health(999) is None

    def test_validate_match_pipeline_no_session(self):
        result = self.monitor.validate_match_pipeline(1)
        assert result["tracked_match_id"] == 1
        assert len(result["stages"]) > 0

    @patch("database.SessionLocal")
    def test_validate_match_pipeline_with_session(self, mock_session_local):
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_session.execute.return_value.fetchone.side_effect = [
            MagicMock(_m=[5], fetchone=lambda: (5,)),
            MagicMock(_m=["LIVE"], fetchone=lambda: ("LIVE",)),
            MagicMock(_m=[None], fetchone=lambda: (None,)),
            MagicMock(_m=[None], fetchone=lambda: (None,)),
            MagicMock(_m=[None], fetchone=lambda: (None,)),
        ]
        result = self.monitor.validate_match_pipeline(1)
        assert result["tracked_match_id"] == 1

    def test_singleton(self):
        m1 = get_match_monitor()
        m2 = get_match_monitor()
        assert m1 is m2
