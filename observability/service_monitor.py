from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any

from observability import config as obs_config
from observability.models import ServiceHeartbeat, ServiceState


class ServiceMonitor:
    def __init__(self) -> None:
        self._heartbeats: dict[str, ServiceHeartbeat] = {}
        self._lock = threading.RLock()
        self._heartbeat_interval = obs_config.OBSERVABILITY_SERVICE_HEARTBEAT_SECONDS

    def record_heartbeat(self, service_name: str, state: ServiceState, **kwargs: Any) -> None:
        with self._lock:
            existing = self._heartbeats.get(service_name)
            if existing:
                existing.state = state
                existing.timestamp = datetime.now(timezone.utc)
                existing.current_task = kwargs.get("current_task", existing.current_task)
                existing.active_threads = kwargs.get("active_threads", existing.active_threads)
                existing.memory_mb = kwargs.get("memory_mb", existing.memory_mb)
                existing.cpu_percent = kwargs.get("cpu_percent", existing.cpu_percent)
                existing.response_time_ms = kwargs.get("response_time_ms", existing.response_time_ms)
                existing.error_count = existing.error_count + kwargs.get("error_count", 0)
            else:
                self._heartbeats[service_name] = ServiceHeartbeat(
                    service_name=service_name,
                    state=state,
                    **{k: v for k, v in kwargs.items() if k in {
                        "current_task", "active_threads", "memory_mb", "cpu_percent",
                        "response_time_ms", "error_count",
                    }},
                )

    def get_heartbeat(self, service_name: str) -> ServiceHeartbeat | None:
        with self._lock:
            hb = self._heartbeats.get(service_name)
            if hb is None:
                return None
            age = (datetime.now(timezone.utc) - hb.timestamp).total_seconds()
            if age > self._heartbeat_interval * 3:
                stale = ServiceHeartbeat(
                    service_name=service_name,
                    state=ServiceState.STOPPED,
                    timestamp=hb.timestamp,
                )
                return stale
            return hb

    def get_all_heartbeats(self) -> dict[str, ServiceHeartbeat]:
        with self._lock:
            result = {}
            for name in list(self._heartbeats.keys()):
                hb = self.get_heartbeat(name)
                if hb:
                    result[name] = hb
            return result

    def get_service_state(self, service_name: str) -> ServiceState | None:
        hb = self.get_heartbeat(service_name)
        return hb.state if hb else None

    def service_summary(self) -> dict[str, Any]:
        heartbeats = self.get_all_heartbeats()
        state_counts: dict[str, int] = {}
        for hb in heartbeats.values():
            state_counts[hb.state.value] = state_counts.get(hb.state.value, 0) + 1
        return {
            "total_services": len(heartbeats),
            "states": state_counts,
            "services": {
                name: {
                    "state": hb.state.value,
                    "last_heartbeat": hb.timestamp.isoformat(),
                    "current_task": hb.current_task,
                    "error_count": hb.error_count,
                }
                for name, hb in heartbeats.items()
            },
        }


_service_monitor_instance: ServiceMonitor | None = None


def get_service_monitor() -> ServiceMonitor:
    global _service_monitor_instance
    if _service_monitor_instance is None:
        _service_monitor_instance = ServiceMonitor()
    return _service_monitor_instance
