import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from database import engine
from incidents.models import Incident

logger = logging.getLogger(__name__)


def attempt_recovery(session: Session, incident: Incident) -> bool:
    incident.recovery_attempts += 1

    if incident.category == "Database":
        return _retry_db_connection(incident)

    if incident.category == "Collector Failure":
        logger.info(
            "INC_%d recovery: collector will retry on next discovery cycle",
            incident.incident_id,
        )
        return True

    if incident.category == "Match Collection":
        logger.info(
            "INC_%d recovery: awaiting next collection tick for match %s",
            incident.incident_id,
            incident.tracked_match_id,
        )
        return True

    logger.debug("INC_%d — no applicable recovery action for category %s",
                  incident.incident_id, incident.category)
    return False


def _retry_db_connection(incident: Incident) -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("INC_%d recovery: DB connection restored", incident.incident_id)
        return True
    except Exception as e:
        logger.warning("INC_%d recovery: DB connection still failing — %s",
                       incident.incident_id, e)
        return False
