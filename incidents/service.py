import hashlib
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from incidents.models import Incident

logger = logging.getLogger(__name__)


def _compute_hash(category: str, module: str, title: str) -> str:
    raw = f"{category}|{module}|{title}"[:256]
    return hashlib.sha256(raw.encode()).hexdigest()


def create_incident(
    session: Session,
    severity: str,
    category: str,
    module: str,
    title: str,
    summary: str = "",
    tracked_match_id: int | None = None,
    collector_name: str | None = None,
) -> Incident:
    incident_hash = _compute_hash(category, module, title)

    existing = (
        session.query(Incident)
        .filter(Incident.incident_hash == incident_hash)
        .first()
    )

    if existing and existing.status in ("OPEN", "ACKNOWLEDGED", "RECOVERING"):
        existing.occurrence_count += 1
        existing.last_detected_at = datetime.now(timezone.utc)
        if summary:
            existing.summary = summary
        session.flush()
        logger.debug(
            "Updated incident INC_%d (%s) — occurrence %d",
            existing.incident_id,
            existing.title,
            existing.occurrence_count,
        )
        return existing

    incident = Incident(
        severity=severity,
        category=category,
        module=module,
        title=title,
        summary=summary,
        incident_hash=incident_hash,
        tracked_match_id=tracked_match_id,
        collector_name=collector_name,
    )
    session.add(incident)
    session.flush()
    logger.info(
        "Created incident INC_%d — %s [%s] %s",
        incident.incident_id,
        severity,
        category,
        title,
    )
    return incident


def resolve_incident(session: Session, incident_id: int) -> Incident | None:
    incident = session.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not incident:
        logger.warning("Cannot resolve — incident INC_%d not found", incident_id)
        return None
    incident.status = "RESOLVED"
    incident.resolved_at = datetime.now(timezone.utc)
    session.flush()
    logger.info("Incident INC_%d resolved", incident_id)
    return incident


def acknowledge_incident(session: Session, incident_id: int) -> Incident | None:
    incident = session.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not incident:
        logger.warning("Cannot acknowledge — incident INC_%d not found", incident_id)
        return None
    incident.status = "ACKNOWLEDGED"
    session.flush()
    logger.info("Incident INC_%d acknowledged", incident_id)
    return incident


def get_open_incidents(session: Session) -> list[Incident]:
    return (
        session.query(Incident)
        .filter(Incident.status.in_(["OPEN", "ACKNOWLEDGED", "RECOVERING"]))
        .order_by(Incident.severity.desc(), Incident.first_detected_at.desc())
        .all()
    )


def list_by_module(session: Session, module: str) -> list[Incident]:
    return (
        session.query(Incident)
        .filter(Incident.module == module)
        .order_by(Incident.created_at.desc())
        .all()
    )
