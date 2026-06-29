from unittest.mock import patch, MagicMock

import pytest

from observability.health import register_health_check, unregister_health_check, make_health_report
from observability.models import HealthStatus
from observability.api import (
    get_platform_health,
    get_service_health,
    validate_platform_pipelines,
    validate_named_pipeline,
    validate_match_pipeline,
    get_platform_metrics,
    get_recent_incidents,
)


class TestAPI:
    def teardown_method(self):
        unregister_health_check("api_test_svc")

    def test_get_platform_health_empty(self):
        health = get_platform_health()
        assert health["total_services"] == 0

    def test_get_platform_health_with_services(self):
        def check():
            return make_health_report("api_test_svc", HealthStatus.HEALTHY, uptime=10.0)
        register_health_check("api_test_svc", check)
        health = get_platform_health()
        assert health["total_services"] >= 1
        assert health["healthy"] >= 1

    def test_get_service_health_found(self):
        def check():
            return make_health_report("found_svc", HealthStatus.HEALTHY, uptime=5.0)
        register_health_check("found_svc", check)
        result = get_service_health("found_svc")
        assert result is not None
        assert result["service_name"] == "found_svc"
        assert result["status"] == "healthy"
        unregister_health_check("found_svc")

    def test_get_service_health_not_found(self):
        assert get_service_health("nonexistent") is None

    def test_validate_named_pipeline_missing(self):
        assert validate_named_pipeline("nonexistent") is None

    def test_validate_pipelines_empty(self):
        results = validate_platform_pipelines()
        assert isinstance(results, dict)
        assert len(results) == 0

    def test_validate_match_pipeline(self):
        result = validate_match_pipeline(1)
        assert result["tracked_match_id"] == 1

    def test_get_platform_metrics(self):
        from observability.metrics import get_metrics
        get_metrics().counter("test").inc(5)
        snap = get_platform_metrics()
        assert "counters" in snap
        assert snap["counters"]["test"] == 5.0
        get_metrics().reset()

    @patch("database.SessionLocal")
    def test_get_recent_incidents(self, mock_session_local):
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_session.execute.return_value.fetchall.return_value = []
        incidents = get_recent_incidents()
        assert len(incidents) == 0
