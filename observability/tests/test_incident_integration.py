from unittest.mock import MagicMock, patch

import pytest

from observability.incident_integration import (
    build_diagnostic_context,
    _get_collector_status,
    _get_environment_info,
)


class TestIncidentIntegration:
    def test_environment_info(self):
        env = _get_environment_info()
        assert "python_version" in env
        assert "platform" in env
        assert "cwd" in env
        assert "pid" in env

    @patch("database.SessionLocal")
    def test_collector_status(self, mock_session_local):
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_session.execute.return_value.fetchone.side_effect = [
            MagicMock(_m=[5], fetchone=lambda: (5,)),
            MagicMock(_m=[3], fetchone=lambda: (3,)),
            MagicMock(_m=[10], fetchone=lambda: (10,)),
            MagicMock(_m=[50], fetchone=lambda: (50,)),
            MagicMock(_m=[100], fetchone=lambda: (100,)),
            MagicMock(_m=[2], fetchone=lambda: (2,)),
        ]
        result = _get_collector_status()
        assert isinstance(result, dict)

    def test_diagnostic_context_basic(self):
        with patch("database.SessionLocal") as mock_sl:
            mock_session = MagicMock()
            mock_sl.return_value = mock_session
            mock_session.execute.return_value.fetchone.return_value = (0,)
            mock_session.execute.return_value.fetchall.return_value = []
            context = build_diagnostic_context(incident_id=1)
            assert "generated_at" in context
            assert "health_snapshot" in context
            assert "current_metrics" in context
            assert "service_status" in context
            assert "collector_status" in context
            assert "database_status" in context
            assert "environment" in context

    def test_diagnostic_context_with_match(self):
        with patch("database.SessionLocal") as mock_sl:
            mock_session = MagicMock()
            mock_sl.return_value = mock_session
            mock_match_row = MagicMock()
            mock_match_row.__getitem__ = lambda self, i: [1, "LIVE", "fs123", "bm456", "Nadal", "Djokovic",
                                                          "Wimbledon", None, True, None, None][i]
            mock_match_row._m = [1, "LIVE", "fs123", "bm456", "Nadal", "Djokovic",
                                "Wimbledon", None, True, None, None]
            mock_session.execute.return_value.fetchone.side_effect = [
                (0,), [], mock_match_row
            ]
            context = build_diagnostic_context(tracked_match_id=1)
            assert "match_context" in context

    @patch("database.SessionLocal")
    def test_enhance_incident_package(self, mock_sl):
        import tempfile
        import os
        mock_session = MagicMock()
        mock_sl.return_value = mock_session
        mock_session.execute.return_value.fetchone.return_value = (0,)
        mock_session.execute.return_value.fetchall.return_value = []
        with tempfile.TemporaryDirectory() as tmpdir:
            result = __import__("observability.incident_integration", fromlist=["enhance_incident_package"]).enhance_incident_package(tmpdir, incident_id=42)
            assert os.path.exists(result)
            content = open(result).read()
            assert "generated_at" in content
