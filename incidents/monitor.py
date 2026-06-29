"""Incident monitor: health checks, detection, recovery, auto-resolve."""
import logging
import os
import shutil
import time
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from database import SessionLocal, check_connection
from incidents.config import (
    COLLECTOR_LABELS,
    COLLECTOR_STALE_SECONDS,
    COLLECTOR_DISCOVERY_STALE_SECONDS,
    LIVE_COLLECTOR_STALE_SECONDS,
    FINALIZER_STALE_SECONDS,
    CPU_THRESHOLD_PERCENT,
    DISK_THRESHOLD_PERCENT,
    MATCH_ODDS_STALE_SECONDS,
    MATCH_SCORE_STALE_SECONDS,
    MEMORY_THRESHOLD_PERCENT,
    MONITOR_INTERVAL_SECONDS,
    UNFINALIZED_STALE_SECONDS,
)
from incidents.models import Incident
from incidents.package_generator import generate_incident_package
from incidents.recovery import attempt_recovery
from incidents.service import create_incident, get_open_incidents, resolve_incident

logger = logging.getLogger(__name__)


def _to_timestamp(val) -> float | None:
    if val is None:
        return None
    if hasattr(val, "timestamp"):
        return val.timestamp()
    if isinstance(val, datetime):
        return val.timestamp()
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(val, fmt)
                return dt.replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(val).timestamp()
        except ValueError:
            pass
    return None

COLLECTOR_QUERIES = {
    "flashscore": "SELECT MAX(discovered_at) FROM flashscorefoundmatches",
    "bettingsite": "SELECT MAX(discovered_at) FROM bettingsitefoundmatches",
    "players": "SELECT MAX(last_updated) FROM players",
    "registry": "SELECT MAX(updated_at) FROM tracked_matches",
}

COLLECTOR_MODULES = {
    "flashscore": "collector.flashscore",
    "bettingsite": "collector.betting_site",
    "players": "collector.tennis_explorer",
    "registry": "registry.service",
    "live_collector": "live_collector",
    "finalizer": "finalizer",
}


def monitor_platform() -> None:
    from incidents.models import Incident as Inc

    Inc.metadata.create_all(bind=__import__("database").engine)

    logger.info("Incident monitor started — interval %ds", MONITOR_INTERVAL_SECONDS)

    while True:
        session = SessionLocal()
        tick_start = time.monotonic()
        try:
            _run_tick(session)
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Monitor tick failed")
        finally:
            session.close()

        elapsed = time.monotonic() - tick_start
        sleep_time = max(1, MONITOR_INTERVAL_SECONDS - elapsed)
        time.sleep(sleep_time)


def _run_tick(session: Session) -> None:
    incidents: list[dict] = []

    incidents.extend(_check_cpu())
    incidents.extend(_check_memory())
    incidents.extend(_check_disk())
    incidents.extend(_check_database(session))
    incidents.extend(_check_collectors(session))
    incidents.extend(_check_live_collector(session))
    incidents.extend(_check_finalizer(session))
    incidents.extend(_check_live_matches(session))
    incidents.extend(_check_unfinalized_finished(session))

    for inc in incidents:
        severity = inc["severity"]
        category = inc["category"]
        module = inc["module"]
        title = inc["title"]

        record = create_incident(
            session,
            severity=severity,
            category=category,
            module=module,
            title=title,
            summary=inc.get("summary", ""),
            tracked_match_id=inc.get("tracked_match_id"),
            collector_name=inc.get("collector_name"),
        )

        from incidents.notifier import send_notification

        if severity == "CRITICAL" and record.occurrence_count == 1:
            try:
                generate_incident_package(session, record)
                send_notification(record)
            except Exception:
                logger.exception("Package/notification failed for INC_%d", record.incident_id)

        if record.status in ("OPEN", "RECOVERING"):
            attempt_recovery(session, record)

    _auto_resolve_healed(session, incidents)

    _check_telegram_bot(session)


def _check_telegram_bot(session: Session) -> None:
    from incidents.telegram_bot import check_commands

    try:
        check_commands(session)
    except Exception:
        logger.exception("Telegram bot command check failed")


def _check_cpu() -> list[dict]:
    try:
        loadavg = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        cpu_pct = (loadavg[0] / cpu_count) * 100
        if cpu_pct > CPU_THRESHOLD_PERCENT:
            return [{
                "severity": "WARNING",
                "category": "Infrastructure",
                "module": "system",
                "title": f"CPU usage critical: {cpu_pct:.1f}%",
                "summary": f"Load average: {loadavg[0]:.2f}/{loadavg[1]:.2f}/{loadavg[2]:.2f} on {cpu_count} cores",
            }]
    except OSError:
        logger.debug("CPU check unavailable")
    return []


def _check_memory() -> list[dict]:
    try:
        total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        avail = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_AVPHYS_PAGES")
        if total > 0:
            used = total - avail
            mem_pct = (used / total) * 100
            if mem_pct > MEMORY_THRESHOLD_PERCENT:
                return [{
                    "severity": "WARNING",
                    "category": "Infrastructure",
                    "module": "system",
                    "title": f"Memory usage critical: {mem_pct:.1f}%",
                    "summary": f"Used: {used // (1024**2)}MB / Total: {total // (1024**2)}MB",
                }]
    except (OSError, AttributeError, ValueError):
        logger.debug("Memory check unavailable")
    return []


def _check_disk() -> list[dict]:
    try:
        usage = shutil.disk_usage("/")
        disk_pct = (usage.used / usage.total) * 100
        if disk_pct > DISK_THRESHOLD_PERCENT:
            return [{
                "severity": "WARNING",
                "category": "Infrastructure",
                "module": "system",
                "title": f"Disk usage critical: {disk_pct:.1f}%",
                "summary": f"Free: {usage.free // (1024**3)}GB / Total: {usage.total // (1024**3)}GB",
            }]
    except OSError:
        logger.debug("Disk check unavailable")
    return []


def _check_database(session: Session) -> list[dict]:
    incidents = []
    if not check_connection():
        incidents.append({
            "severity": "CRITICAL",
            "category": "Database",
            "module": "database",
            "title": "TimescaleDB unreachable",
            "summary": "Database connection check failed (SELECT 1 returned error)",
        })
    return incidents


def _check_collectors(session: Session) -> list[dict]:
    incidents = []
    now = datetime.now(timezone.utc)
    cutoffs = {k: now.timestamp() - COLLECTOR_DISCOVERY_STALE_SECONDS for k in COLLECTOR_QUERIES}

    for key, query in COLLECTOR_QUERIES.items():
        try:
            result = session.execute(text(query))
            last_val = result.scalar()
            if last_val is None:
                continue

            last_ts = _to_timestamp(last_val)
            if last_ts is None:
                continue

            if last_ts < cutoffs[key]:
                label = COLLECTOR_LABELS.get(key, key)
                incidents.append({
                    "severity": "WARNING",
                    "category": "Collector Failure",
                    "module": COLLECTOR_MODULES.get(key, key),
                    "title": f"{label} health check failed",
                    "summary": f"No new data for {COLLECTOR_DISCOVERY_STALE_SECONDS // 3600}h",
                    "collector_name": key,
                })
        except Exception:
            logger.debug("Collector health check failed for %s", key)

    return incidents


def _check_live_collector(session: Session) -> list[dict]:
    incidents = []
    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - LIVE_COLLECTOR_STALE_SECONDS

    # Only flag collector stalls if there are actually LIVE matches
    try:
        live_count = session.execute(text(
            "SELECT count(*) FROM tracked_matches WHERE status = 'LIVE' AND tracking_enabled = TRUE"
        )).scalar() or 0
    except Exception:
        live_count = 0

    if live_count == 0:
        return incidents

    try:
        result = session.execute(text(
            "SELECT MAX(timestamp) FROM live_scores"
        ))
        last_val = result.scalar()
        if last_val is not None:
            last_ts = _to_timestamp(last_val)
            if last_ts is not None and last_ts < cutoff:
                incidents.append({
                    "severity": "ERROR",
                    "category": "Collector Failure",
                    "module": "live_collector",
                    "title": "Live Collector appears stalled",
                    "summary": f"No new score data for {LIVE_COLLECTOR_STALE_SECONDS // 60}min",
                    "collector_name": "live_collector",
                })

        odds_result = session.execute(text(
            "SELECT MAX(timestamp) FROM live_odds"
        ))
        odds_last_val = odds_result.scalar()
        if odds_last_val is not None:
            odds_last_ts = _to_timestamp(odds_last_val)
            if odds_last_ts is not None and odds_last_ts < cutoff:
                incidents.append({
                    "severity": "WARNING",
                    "category": "Collector Failure",
                    "module": "live_collector",
                    "title": "Live Odds Collector appears stalled",
                    "summary": f"No new odds data for {LIVE_COLLECTOR_STALE_SECONDS // 60}min",
                    "collector_name": "live_collector",
                })
    except Exception:
        logger.debug("Live collector health check failed")
    return incidents


def _check_finalizer(session: Session) -> list[dict]:
    incidents = []
    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - FINALIZER_STALE_SECONDS
    try:
        result = session.execute(text(
            "SELECT MAX(finalized_at) FROM completed_matches"
        ))
        last_val = result.scalar()
        if last_val is not None:
            last_ts = _to_timestamp(last_val)
            if last_ts is not None and last_ts < cutoff:
                incidents.append({
                    "severity": "WARNING",
                    "category": "Collector Failure",
                    "module": "finalizer",
                    "title": "Match Finalizer appears stalled",
                    "summary": f"No matches finalized for {FINALIZER_STALE_SECONDS // 60}min",
                    "collector_name": "finalizer",
                })
    except Exception:
        logger.debug("Finalizer health check failed")
    return incidents


def _check_live_matches(session: Session) -> list[dict]:
    incidents = []
    now = datetime.now(timezone.utc)

    try:
        rows = session.execute(text(
            "SELECT id, flashscore_match_id, player1_name, player2_name "
            "FROM tracked_matches WHERE status = 'LIVE' AND tracking_enabled = TRUE"
        )).fetchall()
    except Exception:
        return []

    score_cutoff = now.timestamp() - MATCH_SCORE_STALE_SECONDS
    odds_cutoff = now.timestamp() - MATCH_ODDS_STALE_SECONDS

    for row in rows:
        match_id = row[0]
        fs_id = row[1]
        p1 = row[2] or "?"
        p2 = row[3] or "?"

        try:
            score_result = session.execute(
                text("SELECT MAX(timestamp) FROM live_scores WHERE tracked_match_id = :mid"),
                {"mid": match_id},
            )
            last_score = score_result.scalar()
        except Exception:
            last_score = None

        try:
            odds_result = session.execute(
                text("SELECT MAX(timestamp) FROM live_odds WHERE tracked_match_id = :mid"),
                {"mid": match_id},
            )
            last_odds = odds_result.scalar()
        except Exception:
            last_odds = None

        score_ts = _to_timestamp(last_score)
        odds_ts = _to_timestamp(last_odds)

        if score_ts is not None and score_ts < score_cutoff:
            incidents.append({
                "severity": "WARNING",
                "category": "Match Collection",
                "module": "live_collector",
                "title": f"Stale scores: {p1} vs {p2}",
                "summary": f"No score update for {fs_id} in {MATCH_SCORE_STALE_SECONDS}s",
                "tracked_match_id": match_id,
                "collector_name": "flashscore",
            })

        if odds_ts is not None and odds_ts < odds_cutoff:
            incidents.append({
                "severity": "WARNING",
                "category": "Match Collection",
                "module": "live_collector",
                "title": f"Stale odds: {p1} vs {p2}",
                "summary": f"No odds update for {fs_id} in {MATCH_ODDS_STALE_SECONDS}s",
                "tracked_match_id": match_id,
                "collector_name": "bettingsite",
            })

    return incidents


def _check_unfinalized_finished(session: Session) -> list[dict]:
    incidents = []
    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - UNFINALIZED_STALE_SECONDS

    try:
        rows = session.execute(text(
            "SELECT tm.id, tm.flashscore_match_id, tm.player1_name, tm.player2_name, tm.actual_finish "
            "FROM tracked_matches tm "
            "LEFT JOIN completed_matches cm ON cm.tracked_match_id = tm.id "
            "WHERE tm.status = 'FINISHED' AND cm.id IS NULL"
        )).fetchall()
    except Exception:
        return []

    for row in rows:
        match_id = row[0]
        fs_id = row[1]
        p1 = row[2] or "?"
        p2 = row[3] or "?"
        actual_finish = row[4]

        if actual_finish is not None:
            finish_ts = _to_timestamp(actual_finish)

            if finish_ts is not None and finish_ts < cutoff:
                incidents.append({
                    "severity": "ERROR",
                    "category": "Data Validation",
                    "module": "finalizer",
                    "title": f"Match finished but not finalized: {p1} vs {p2}",
                    "summary": f"Match {fs_id} finished but finalizer never ran (stale {UNFINALIZED_STALE_SECONDS}s)",
                    "tracked_match_id": match_id,
                    "collector_name": "finalizer",
                })

    return incidents


def _auto_resolve_healed(session: Session, current_incidents: list[dict]) -> None:
    open_incidents = get_open_incidents(session)
    current_sigs = {
        (inc["category"], inc["module"], inc["title"]) for inc in current_incidents
    }

    for incident in open_incidents:
        sig = (incident.category, incident.module, incident.title)
        if sig not in current_sigs:
            resolve_incident(session, incident.incident_id)
            logger.info(
                "Auto-resolved INC_%d — condition no longer detected: %s",
                incident.incident_id,
                incident.title,
            )
