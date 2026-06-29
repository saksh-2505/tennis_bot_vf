"""Main platform loop. Discovery, status monitoring, finalizer, live collector spawn."""
import logging
import threading
import time
from datetime import datetime, timezone, timedelta

from config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# Status Monitor (DB-only, no network — the default infinite loop)
# ============================================================================


def update_match_statuses() -> int:
    """Transition matches from DISCOVERED/SCHEDULED → LIVE when their
    scheduled start time has passed.

    Returns the number of matches whose status was changed.

    This function performs NO network calls — it is a pure database read
    + time comparison.  All datetimes are treated as UTC.

    .. note::

        FINISHED is NOT set here.  The live scraper (Phase 2 live data
        collection) is responsible for marking matches as FINISHED.
    """
    import database as db
    from models.tracked_match import TrackedMatch

    now_utc = datetime.now(timezone.utc)
    updated = 0

    with db.SessionLocal() as session:
        matches = (
            session.query(TrackedMatch)
            .filter(
                TrackedMatch.tracking_enabled == True,               # noqa: E712
                TrackedMatch.scheduled_start.isnot(None),
                TrackedMatch.status.in_(["DISCOVERED", "SCHEDULED"]),
            )
            .all()
        )

        for m in matches:
            if m.scheduled_start is None:
                continue

            sched = m.scheduled_start
            if sched.tzinfo is None:
                sched = sched.replace(tzinfo=timezone.utc)

            old_status = m.status
            if now_utc >= sched:
                m.status = "LIVE"
                m.updated_at = now_utc
                updated += 1
                logger.info(
                    "Match %s (%s vs %s) transitioned %s → LIVE",
                    m.flashscore_match_id, m.player1_name, m.player2_name,
                    old_status,
                )

        if updated:
            session.commit()

    return updated


# ============================================================================
# Discovery Cycle (one-shot scrape — called at startup and on schedule)
# ============================================================================


def run_discovery_cycle() -> dict:
    """Execute one complete discovery cycle and return a summary dict.

    Each phase is wrapped in try/except so a single module failure never
    takes down the platform.
    """
    from collector.flashscore import discover_matches as discover_flashscore
    from collector.flashscore import save_matches_to_db as save_flashscore
    from collector.betting_site import discover_matches as discover_bettingsite
    from collector.betting_site import save_matches_to_db as save_bettingsite
    from registry.service import build_match_registry

    summary: dict = {}

    # -- Phase 1: Flashscore ----------------------------------------------
    fs_matches = []
    try:
        fs_matches = discover_flashscore()
        fs_saved = save_flashscore(fs_matches)
        summary["flashscore_discovered"] = len(fs_matches)
        summary["flashscore_saved"] = fs_saved
    except Exception:
        logger.exception("Flashscore discovery failed")
        summary["flashscore_discovered"] = 0
        summary["flashscore_saved"] = 0

    # -- Phase 2: Betting Site --------------------------------------------
    try:
        bt_matches = discover_bettingsite(fs_matches)
        bt_saved = save_bettingsite(bt_matches)
        summary["bettingsite_discovered"] = len(bt_matches)
        summary["bettingsite_saved"] = bt_saved
    except Exception:
        logger.exception("Betting site discovery failed")
        summary["bettingsite_discovered"] = 0
        summary["bettingsite_saved"] = 0

    # -- Phase 3: Players (missing only) ----------------------------------
    try:
        player_names: set[str] = set()
        for m in fs_matches:
            player_names.add(m.player_a)
            player_names.add(m.player_b)

        new_players, failed_players = _update_missing_players(
            list(player_names)
        )
        summary["players_added"] = new_players
        summary["players_failed"] = failed_players
    except Exception:
        logger.exception("Player update failed")
        summary["players_added"] = 0
        summary["players_failed"] = 0

    # -- Phase 4: Match Registry ------------------------------------------
    try:
        registry = build_match_registry()
        summary["registry_count"] = len(registry)
    except Exception:
        logger.exception("Match registry build failed")
        summary["registry_count"] = 0

    return summary


# ============================================================================
# Platform Loop — runs discovery on schedule + status monitor continuously
# ============================================================================


def _check_force_rediscovery() -> bool:
    """Return True if no LIVE matches and no upcoming matches are tracked.

    When all matches have finished and none are upcoming, the system is
    stuck — trigger an early discovery cycle.
    """
    import database as db
    from models.tracked_match import TrackedMatch
    from datetime import datetime, timezone
    from sqlalchemy import func

    with db.SessionLocal() as session:
        live = session.query(func.count(TrackedMatch.id)).filter(
            TrackedMatch.status.in_(["LIVE", "DISCOVERED", "SCHEDULED"]),
            TrackedMatch.tracking_enabled.is_(True),
        ).scalar() or 0

        return live == 0


def run_platform() -> None:
    """Main platform loop.

    * Runs discovery at startup.
    * Then enters a status-monitor loop that runs every
      ``STATUS_CHECK_INTERVAL_SECONDS``.
    * Discovery is re-executed every ``DISCOVERY_INTERVAL_SECONDS`` (default
      12 h) while the loop is alive.  If ``DISCOVERY_ENABLED`` is ``false``,
      discovery only runs once at startup.
    * If all matches have expired (zero LIVE/DISCOVERED/SCHEDULED), an
      early discovery cycle is triggered to recover from a stale state.

    The loop never scrapes — ``update_match_statuses()`` is a pure DB
    comparison of ``scheduled_start`` against the current UTC time.
    """
    logger.info("Platform starting — running initial discovery cycle")
    _run_and_log_discovery()
    last_discovery = time.monotonic()

    if not settings.DISCOVERY_ENABLED:
        logger.info("Discovery scheduled disabled — entering status-monitor loop only")

    logger.info(
        "Entering status-monitor loop (interval=%ds, discovery=%ds)",
        settings.STATUS_CHECK_INTERVAL_SECONDS,
        settings.DISCOVERY_INTERVAL_SECONDS,
    )

    # Spawn live collector in a background daemon thread
    _spawn_live_collector()

    while True:
        loop_start = time.monotonic()

        # ---- Status check (DISCOVERED → LIVE) ---------------------------
        try:
            transitions = update_match_statuses()
            total_live = _count_by_status("LIVE")
            total_scheduled = _count_by_status("SCHEDULED")
            total_discovered = _count_by_status("DISCOVERED")
            logger.info(
                "Status: %d transitioned to LIVE, %d currently LIVE, "
                "%d SCHEDULED, %d DISCOVERED",
                transitions, total_live, total_scheduled, total_discovered,
            )

            # Auto-rediscovery: if zero LIVE/SCHEDULED/DISCOVERED matches
            # and enough time has passed since last discovery, force re-run
            if settings.DISCOVERY_ENABLED:
                since_last = loop_start - last_discovery
                min_recovery_interval = 300  # 5 min between rediscovery attempts
                if since_last >= min_recovery_interval and _check_force_rediscovery():
                    logger.warning(
                        "Zero LIVE/SCHEDULED/DISCOVERED matches — "
                        "forcing early discovery cycle (%.0f s since last)",
                        since_last,
                    )
                    _run_and_log_discovery()
                    last_discovery = loop_start
        except Exception:
            logger.exception("Status monitor tick failed")

        # ---- Finalizer (FINISHED → completed_matches) --------------------
        try:
            finalized = _run_finalizer()
            if finalized:
                logger.info("Finalized %d matches", finalized)
        except Exception:
            logger.exception("Match finalizer tick failed")

        # ---- Scheduled discovery -----------------------------------------
        if settings.DISCOVERY_ENABLED:
            try:
                since_last = loop_start - last_discovery
                if since_last >= settings.DISCOVERY_INTERVAL_SECONDS:
                    logger.info(
                        "Scheduled discovery triggered (%.0f s since last run)",
                        since_last,
                    )
                    _run_and_log_discovery()
                    last_discovery = loop_start
            except Exception:
                logger.exception("Scheduled discovery failed")

        # ---- Sleep -------------------------------------------------------
        elapsed = time.monotonic() - loop_start
        remaining = max(0, settings.STATUS_CHECK_INTERVAL_SECONDS - elapsed)
        time.sleep(remaining)


# ============================================================================
# Internal helpers
# ============================================================================


def _update_missing_players(player_names: list[str]) -> tuple[int, int]:
    """Update only players that are not yet in the ``players`` table."""
    import database as db
    from models.player import Player

    with db.SessionLocal() as session:
        existing = {row[0] for row in session.query(Player.full_name).all()}

    missing = [n for n in player_names if n not in existing]
    if not missing:
        return 0, 0

    from collector.tennis_explorer import update_players

    results = update_players(missing)
    added = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    return added, failed


def _run_and_log_discovery() -> None:
    start = time.monotonic()
    summary = run_discovery_cycle()
    elapsed = time.monotonic() - start

    logger.info(
        "Flashscore: %(flashscore_discovered)d matches discovered, "
        "%(flashscore_saved)d new saved",
        summary,
    )
    logger.info(
        "Betting site: %(bettingsite_discovered)d markets discovered, "
        "%(bettingsite_saved)d new saved",
        summary,
    )
    logger.info(
        "Players: %(players_added)d new added, %(players_failed)d failed",
        summary,
    )
    logger.info("Registry: %(registry_count)d tracked matches", summary)
    logger.info("Discovery cycle completed in %.1f seconds", elapsed)


def _count_by_status(status: str) -> int:
    """Return the number of tracked matches with the given status."""
    import database as db
    from models.tracked_match import TrackedMatch

    with db.SessionLocal() as session:
        return (
            session.query(TrackedMatch)
            .filter(TrackedMatch.status == status)
            .count()
        )


def _run_finalizer() -> int:
    """Run the match finalizer and return the number of finalized matches."""
    import database as db
    from finalizer.service import run_match_finalizer

    with db.SessionLocal() as session:
        completed = run_match_finalizer(session)
        return len(completed)


def _spawn_live_collector() -> None:
    """Start the live collector in a daemon background thread."""
    from live_collector.service import run_live_collection_loop

    t = threading.Thread(target=run_live_collection_loop, daemon=True)
    t.start()
    logger.info("Live collector thread spawned")
