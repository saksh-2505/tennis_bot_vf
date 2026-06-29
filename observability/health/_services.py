from __future__ import annotations

import time
from datetime import datetime, timezone

from observability.health import make_health_report, register_health_check
from observability.models import HealthStatus


def _check_incident_manager() -> HealthReport:
    try:
        from database import SessionLocal
        from sqlalchemy import text
        session = SessionLocal()
        try:
            result = session.execute(text(
                "SELECT COUNT(*), MAX(last_detected_at) FROM incidents"
            ))
            row = result.fetchone()
            count = row[0] if row else 0
            max_ts = row[1] if row else None
            return make_health_report(
                service_name="Incident Manager",
                status=HealthStatus.HEALTHY,
                uptime=time.time(),
                last_success=max_ts or datetime.now(timezone.utc),
                processed_items=count,
                details={"open_incidents": count, "last_incident": max_ts.isoformat() if max_ts else None},
            )
        finally:
            session.close()
    except Exception:
        return make_health_report(
            service_name="Incident Manager",
            status=HealthStatus.UNKNOWN,
            uptime=time.time(),
            details={"error": "could not query incidents table"},
        )


def _check_notification_service() -> HealthReport:
    try:
        from shared.notify import _enabled
        enabled = _enabled
    except Exception:
        enabled = False

    return make_health_report(
        service_name="Notification Service",
        status=HealthStatus.HEALTHY if enabled else HealthStatus.DEGRADED,
        uptime=time.time(),
        details={"telegram_enabled": enabled},
    )


def register_service_health_checks() -> None:
    register_health_check("Incident Manager", _check_incident_manager)
    register_health_check("Notification Service", _check_notification_service)
