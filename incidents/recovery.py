"""Auto-recovery actions for incidents."""
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import engine
from incidents.config import MATCH_SCORE_STALE_SECONDS, MATCH_ODDS_STALE_SECONDS
from incidents.models import Incident

logger = logging.getLogger(__name__)


def attempt_recovery(session: Session, incident: Incident) -> bool:
    incident.recovery_attempts += 1

    if incident.category == "Database":
        return _retry_db_connection(incident)

    if incident.category == "Collector Failure":
        return _retry_collector(session, incident)

    if incident.category == "Match Collection":
        return _retry_live_match(session, incident)

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


def _retry_collector(session: Session, incident: Incident) -> bool:
    """Attempt to kick a stalled collector by probing it."""
    module = incident.module

    if module == "live_collector":
        # Probe the live score endpoint for any LIVE match to see if
        # data is actually flowing or if the collector is truly stuck.
        try:
            result = session.execute(text(
                "SELECT tm.id, tm.flashscore_match_id FROM tracked_matches tm "
                "WHERE tm.status = 'LIVE' AND tm.tracking_enabled = TRUE "
                "LIMIT 1"
            ))
            row = result.fetchone()
            if row:
                match_id, fs_id = row
                url = f"https://www.flashscore.mobi/match/{fs_id}/"
                with httpx.Client(timeout=10, follow_redirects=True) as client:
                    client.get(url, headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Linux; Android 14; SM-S928B) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/125.0.0.0 Mobile Safari/537.36"
                        ),
                    })
                logger.info(
                    "INC_%d recovery: probed Flashscore mobile for match %s — OK",
                    incident.incident_id, fs_id,
                )
            else:
                logger.info(
                    "INC_%d recovery: no LIVE matches to probe",
                    incident.incident_id,
                )
            return True
        except Exception as e:
            logger.warning(
                "INC_%d recovery: live probe failed — %s",
                incident.incident_id, e,
            )
            return False

    # For discovery collectors, just log that they'll retry
    logger.info(
        "INC_%d recovery: collector %s will retry on next discovery cycle",
        incident.incident_id, module,
    )
    return True


def _retry_live_match(session: Session, incident: Incident) -> bool:
    """Attempt a forced re-fetch for a stale match."""
    match_id = incident.tracked_match_id
    if match_id is None:
        logger.info("INC_%d recovery: no match_id attached", incident.incident_id)
        return False

    try:
        row = session.execute(text(
            "SELECT flashscore_match_id, betting_market_id FROM tracked_matches "
            "WHERE id = :mid",
            {"mid": match_id},
        )).fetchone()
        if not row:
            logger.warning("INC_%d recovery: match %d not found", incident.incident_id, match_id)
            return False

        fs_id, bm_id = row

        if fs_id:
            url = f"https://www.flashscore.mobi/match/{fs_id}/"
            with httpx.Client(timeout=10, follow_redirects=True) as client:
                resp = client.get(url, headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Linux; Android 14; SM-S928B) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Mobile Safari/537.36"
                    ),
                })
                resp.raise_for_status()
            logger.info(
                "INC_%d recovery: forced Flashscore poll for match %s — %d",
                incident.incident_id, fs_id, resp.status_code,
            )

        if bm_id:
            with httpx.Client(timeout=10) as client:
                resp = client.post(
                    "https://odd.ocric99.com/ws/getMarketDataNew",
                    data={"market_ids[]": bm_id},
                )
            logger.info(
                "INC_%d recovery: forced odds poll for market %s — %d",
                incident.incident_id, bm_id, resp.status_code,
            )

        return True
    except Exception as e:
        logger.warning(
            "INC_%d recovery: forced poll failed — %s",
            incident.incident_id, e,
        )
        return False
