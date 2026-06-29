from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Callable

from observability import config as obs_config
from observability.models import HealthReport, HealthStatus
from observability.utils import get_cpu_usage, get_memory_usage

_health_registry: dict[str, Callable[[], HealthReport]] = {}
_last_health: dict[str, tuple[float, HealthReport]] = {}
_STALE_THRESHOLD = obs_config.OBSERVABILITY_HEALTH_STALE_SECONDS


def register_health_check(service_name: str, fn: Callable[[], HealthReport]) -> None:
    _health_registry[service_name] = fn


def unregister_health_check(service_name: str) -> None:
    _health_registry.pop(service_name, None)
    _last_health.pop(service_name, None)


def get_health(service_name: str) -> HealthReport | None:
    fn = _health_registry.get(service_name)
    if fn is None:
        return None
    try:
        report = fn()
        _last_health[service_name] = (time.time(), report)
        return report
    except Exception:
        cached = _last_health.get(service_name)
        if cached:
            return cached[1]
        return HealthReport(
            service_name=service_name,
            status=HealthStatus.UNKNOWN,
            uptime=0.0,
            last_success=None,
            last_error=datetime.now(timezone.utc),
            heartbeat_time=None,
            active_tasks=0,
            processed_items=0,
            average_latency_ms=0.0,
            cpu_usage=0.0,
            memory_usage=0.0,
            details={"error": "health check raised exception"},
        )


def get_all_health() -> dict[str, HealthReport]:
    return {name: get_health(name) for name in list(_health_registry.keys())}


def get_platform_health_summary() -> dict[str, Any]:
    reports = get_all_health()
    total = len(reports)
    healthy = sum(1 for r in reports.values() if r.status == HealthStatus.HEALTHY)
    degraded = sum(1 for r in reports.values() if r.status == HealthStatus.DEGRADED)
    unhealthy = sum(1 for r in reports.values() if r.status == HealthStatus.UNHEALTHY)
    unknown = sum(1 for r in reports.values() if r.status == HealthStatus.UNKNOWN)
    return {
        "total_services": total,
        "healthy": healthy,
        "degraded": degraded,
        "unhealthy": unhealthy,
        "unknown": unknown,
        "services": {name: {"status": r.status.value, "uptime": r.uptime} for name, r in reports.items()},
    }


def make_health_report(
    service_name: str,
    status: HealthStatus,
    uptime: float,
    last_success: datetime | None = None,
    last_error: datetime | None = None,
    heartbeat_time: datetime | None = None,
    active_tasks: int = 0,
    processed_items: int = 0,
    average_latency_ms: float = 0.0,
    details: dict[str, Any] | None = None,
) -> HealthReport:
    return HealthReport(
        service_name=service_name,
        status=status,
        uptime=uptime,
        last_success=last_success,
        last_error=last_error,
        heartbeat_time=heartbeat_time,
        active_tasks=active_tasks,
        processed_items=processed_items,
        average_latency_ms=average_latency_ms,
        cpu_usage=get_cpu_usage(),
        memory_usage=get_memory_usage(),
        details=details,
    )
