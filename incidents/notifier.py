import logging
import os

import httpx

from incidents.config import TELEGRAM_ENABLED
from incidents.models import Incident

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

_enabled = TELEGRAM_ENABLED and bool(BOT_TOKEN and CHAT_ID)

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
    if not _enabled:
        logger.debug("Telegram disabled — skipping incident notification")
        return False

    try:
        text = _format_incident_alert(incident)
        resp = httpx.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text},
            timeout=15,
        )
        ok = resp.is_success
        if ok:
            logger.info("Telegram alert sent for INC_%d", incident.incident_id)
        else:
            logger.warning(
                "Telegram send failed (HTTP %d) for INC_%d: %s",
                resp.status_code,
                incident.incident_id,
                resp.text[:200],
            )
        return ok
    except Exception as e:
        logger.warning("Telegram alert failed for INC_%d: %s", incident.incident_id, e)
        return False
