import time
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from observability.service_monitor import get_service_monitor, ServiceMonitor
from observability.models import ServiceState


class TestServiceMonitor:
    def setup_method(self):
        self.monitor = ServiceMonitor()

    def test_empty_monitor(self):
        assert self.monitor.get_all_heartbeats() == {}

    def test_record_and_get_heartbeat(self):
        self.monitor.record_heartbeat("test_svc", ServiceState.RUNNING, current_task="working")
        hb = self.monitor.get_heartbeat("test_svc")
        assert hb is not None
        assert hb.service_name == "test_svc"
        assert hb.state == ServiceState.RUNNING
        assert hb.current_task == "working"

    def test_stale_heartbeat_reports_stopped(self):
        self.monitor._heartbeat_interval = 0.001
        self.monitor.record_heartbeat("stale_svc", ServiceState.RUNNING)
        import time
        time.sleep(0.01)
        hb = self.monitor.get_heartbeat("stale_svc")
        assert hb.state == ServiceState.STOPPED

    def test_nonexistent_heartbeat(self):
        assert self.monitor.get_heartbeat("nonexistent") is None

    def test_get_all_heartbeats(self):
        self.monitor.record_heartbeat("a", ServiceState.RUNNING)
        self.monitor.record_heartbeat("b", ServiceState.IDLE)
        all_hb = self.monitor.get_all_heartbeats()
        assert "a" in all_hb
        assert "b" in all_hb

    def test_service_summary(self):
        self.monitor.record_heartbeat("s1", ServiceState.RUNNING)
        self.monitor.record_heartbeat("s2", ServiceState.RUNNING)
        self.monitor.record_heartbeat("s3", ServiceState.IDLE)
        summary = self.monitor.service_summary()
        assert summary["total_services"] == 3
        assert summary["states"]["running"] == 2
        assert summary["states"]["idle"] == 1

    def test_error_count_accumulates(self):
        self.monitor.record_heartbeat("err_svc", ServiceState.RUNNING)
        self.monitor.record_heartbeat("err_svc", ServiceState.RUNNING, error_count=3)
        self.monitor.record_heartbeat("err_svc", ServiceState.RUNNING, error_count=2)
        hb = self.monitor.get_heartbeat("err_svc")
        assert hb.error_count == 5

    def test_singleton(self):
        m1 = get_service_monitor()
        m2 = get_service_monitor()
        assert m1 is m2
