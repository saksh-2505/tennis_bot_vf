from unittest.mock import patch

import pytest

from observability.health import (
    get_health,
    get_all_health,
    get_platform_health_summary,
    make_health_report,
    register_health_check,
    unregister_health_check,
)
from observability.models import HealthStatus


class TestHealth:
    def teardown_method(self):
        unregister_health_check("test_service")

    def test_register_and_get(self):
        def check():
            return make_health_report("test_service", HealthStatus.HEALTHY, uptime=100.0)
        register_health_check("test_service", check)
        report = get_health("test_service")
        assert report is not None
        assert report.service_name == "test_service"
        assert report.status == HealthStatus.HEALTHY
        assert report.uptime == 100.0

    def test_get_nonexistent(self):
        assert get_health("nonexistent") is None

    def test_get_all(self):
        def check_a():
            return make_health_report("svc_a", HealthStatus.HEALTHY, uptime=1.0)
        def check_b():
            return make_health_report("svc_b", HealthStatus.DEGRADED, uptime=2.0)
        register_health_check("svc_a", check_a)
        register_health_check("svc_b", check_b)
        all_h = get_all_health()
        assert "svc_a" in all_h
        assert "svc_b" in all_h
        assert all_h["svc_a"].status == HealthStatus.HEALTHY
        unregister_health_check("svc_a")
        unregister_health_check("svc_b")

    def test_platform_health_summary(self):
        def check_ok():
            return make_health_report("ok", HealthStatus.HEALTHY, uptime=1.0)
        def check_bad():
            return make_health_report("bad", HealthStatus.UNHEALTHY, uptime=2.0)
        register_health_check("ok", check_ok)
        register_health_check("bad", check_bad)
        summary = get_platform_health_summary()
        assert summary["total_services"] == 2
        assert summary["healthy"] == 1
        assert summary["unhealthy"] == 1
        unregister_health_check("ok")
        unregister_health_check("bad")

    def test_health_check_exception_cached(self):
        call_count = [0]
        def check():
            call_count[0] += 1
            if call_count[0] == 1:
                return make_health_report("flaky", HealthStatus.HEALTHY, uptime=1.0)
            raise RuntimeError("fail")
        register_health_check("flaky", check)
        r1 = get_health("flaky")
        assert r1.status == HealthStatus.HEALTHY
        r2 = get_health("flaky")
        assert r2.status == HealthStatus.HEALTHY
        unregister_health_check("flaky")

    def test_unregister(self):
        def check():
            return make_health_report("tmp", HealthStatus.HEALTHY, uptime=1.0)
        register_health_check("tmp", check)
        assert get_health("tmp") is not None
        unregister_health_check("tmp")
        assert get_health("tmp") is None

    def test_make_report_includes_cpu_mem(self):
        report = make_health_report("test", HealthStatus.HEALTHY, uptime=10.0)
        assert report.cpu_usage >= 0.0
        assert report.memory_usage >= 0.0
