"""Structured event logging to TimescaleDB hypertable (system_events).

Usage:
    from shared.event_logger import log_event, log_incident_event
    log_event("ERROR", "collector.flashscore", "Fetch failed", details={"url": "..."})
    log_incident_event("created", "incidents.monitor", 42, "DB connection lost")
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def log_event(
    level: str,
    source: str,
    message: str,
    details: dict[str, Any] | None = None,
    incident_id: int | None = None,
    tracked_match_id: int | None = None,
) -> str:
    from database import SessionLocal
    from models.system_event import SystemEvent

    event = SystemEvent(
        timestamp=datetime.now(timezone.utc),
        level=level,
        source=source,
        message=message,
        details=json.dumps(details) if details else None,
        incident_id=incident_id,
        tracked_match_id=tracked_match_id,
    )
    try:
        with SessionLocal() as session:
            session.add(event)
            session.commit()
    except Exception:
        logger.exception("Failed to log event to TimescaleDB")
    return event.event_id


def log_incident_event(
    event_type: str,
    source: str,
    incident_id: int,
    message: str,
    details: dict[str, Any] | None = None,
) -> str:
    return log_event(
        level="INFO",
        source=source,
        message=f"[Incident {event_type}] {message}",
        details=details,
        incident_id=incident_id,
    )


def log_error(
    source: str,
    message: str,
    details: dict[str, Any] | None = None,
    tracked_match_id: int | None = None,
) -> str:
    return log_event(
        level="ERROR",
        source=source,
        message=message,
        details=details,
        tracked_match_id=tracked_match_id,
    )
