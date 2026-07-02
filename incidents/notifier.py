"""Telegram alert sending for CRITICAL incidents."""
import logging

from incidents.config import TELEGRAM_ENABLED
from incidents.models import Incident
from shared.event_logger import log_incident_event
from shared.notify import send_telegram as _send_telegram

logger = logging.getLogger(__name__)

SEVERITY_ICONS = {
    "INFO": "\u2139\ufe0f",
    "WARNING": "\u26a0\ufe0f",
    "ERROR": "\u274c",
    "CRITICAL": "\U0001f534",
}


def _format_incident_alert(incident: Incident) -> str:
    icon = SEVERITY_ICONS.get(incident.severity, "")
    lines = [
        f"{icon} {incident.severity} — {incident.category}",
        f"Module: {incident.module}",
        f"Title: {incident.title}",
        f"Summary: {incident.summary[:300]}",
        f"Incident ID: INC_{incident.incident_id}",
    ]
    if incident.tracked_match_id:
        lines.insert(-1, f"Match: {incident.tracked_match_id}")
    if incident.collector_name:
        lines.insert(-1, f"Collector: {incident.collector_name}")
    lines.append(
        f"Time: {incident.first_detected_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        if incident.first_detected_at
        else ""
    )
    lines.append(f"Occurrences: {incident.occurrence_count}")
    return "\n".join(lines)


def send_notification(incident: Incident) -> bool:
    if not TELEGRAM_ENABLED:
        logger.debug("Telegram disabled — skipping incident notification")
        return False

    try:
        text = _format_incident_alert(incident)
        ok = _send_telegram(text)
        if ok:
            logger.info("Telegram alert sent for INC_%d", incident.incident_id)
            try:
                log_incident_event(
                    "notified",
                    "incidents.notifier",
                    incident.incident_id,
                    incident.title,
                )
            except Exception:
                pass
        else:
            logger.warning("Telegram API rejected message for INC_%d", incident.incident_id)
        return ok
    except Exception as e:
        logger.warning("Telegram alert failed for INC_%d: %s", incident.incident_id, e)
        return False
