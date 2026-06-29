from __future__ import annotations

import time
from datetime import datetime, timezone

from observability.health import make_health_report, register_health_check
from observability.models import HealthStatus


def _check_flashscore_discovery() -> HealthReport:
    return _check_collector_by_query(
        "Flashscore Discovery",
        "collector.flashscore",
        "flashscorefoundmatches",
        "discovered_at",
    )


def _check_betting_discovery() -> HealthReport:
    return _check_collector_by_query(
        "Betting Discovery",
        "collector.betting_site",
        "bettingsitefoundmatches",
        "discovered_at",
    )


def _check_player_collector() -> HealthReport:
    return _check_collector_by_query(
        "Player Collector",
        "collector.tennis_explorer",
        "players",
        "updated_at",
    )


def _check_match_registry() -> HealthReport:
    return _check_collector_by_query(
        "Match Registry",
        "registry.service",
        "tracked_matches",
        "updated_at",
    )


def _check_live_collector() -> HealthReport:
    from observability import config as obs_config
    score_stale = obs_config.OBSERVABILITY_MATCH_SCORE_STALE_SECONDS
    try:
        from database import SessionLocal
        from sqlalchemy import text
        session = SessionLocal()
        try:
            result = session.execute(text(
                "SELECT MAX(timestamp) FROM live_scores"
            ))
            max_ts = result.scalar()
            result2 = session.execute(text(
                "SELECT MAX(timestamp) FROM live_odds"
            ))
            max_odds_ts = result2.scalar()
            now = datetime.now(timezone.utc)
            score_ok = max_ts and (now - max_ts).total_seconds() < score_stale
            odds_ok = max_odds_ts and (now - max_odds_ts).total_seconds() < score_stale
            status = HealthStatus.HEALTHY
            if not score_ok or not odds_ok:
                status = HealthStatus.DEGRADED
            return make_health_report(
                service_name="Live Collector",
                status=status,
                uptime=time.time(),
                last_success=max_ts or datetime.now(timezone.utc),
                last_error=None if status == HealthStatus.HEALTHY else datetime.now(timezone.utc),
                details={
                    "last_score_timestamp": max_ts.isoformat() if max_ts else None,
                    "last_odds_timestamp": max_odds_ts.isoformat() if max_odds_ts else None,
                },
            )
        finally:
            session.close()
    except Exception as e:
        return make_health_report(
            service_name="Live Collector",
            status=HealthStatus.UNHEALTHY,
            uptime=time.time(),
            last_error=datetime.now(timezone.utc),
            details={"error": str(e)},
        )


def _check_match_finalizer() -> HealthReport:
    return _check_collector_by_query(
        "Match Finalizer",
        "finalizer.service",
        "completed_matches",
        "finalized_at",
    )


def _check_collector_by_query(
    service_name: str,
    module_name: str,
    table: str,
    time_column: str,
) -> HealthReport:
    from observability import config as obs_config
    try:
        from database import SessionLocal
        from sqlalchemy import text
        session = SessionLocal()
        try:
            result = session.execute(text(
                f"SELECT COUNT(*), MAX({time_column}) FROM {table}"
            ))
            row = result.fetchone()
            count = row[0] if row else 0
            max_ts = row[1] if row else None
            now = datetime.now(timezone.utc)
            if max_ts is None:
                status = HealthStatus.UNKNOWN
            elif (now - max_ts).total_seconds() > obs_config.OBSERVABILITY_METRICS_WINDOW_SECONDS:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            return make_health_report(
                service_name=service_name,
                status=status,
                uptime=time.time(),
                last_success=max_ts or datetime.now(timezone.utc),
                last_error=None if max_ts else datetime.now(timezone.utc),
                processed_items=count,
                details={"table": table, "row_count": count, "last_timestamp": max_ts.isoformat() if max_ts else None},
            )
        finally:
            session.close()
    except Exception as e:
        return make_health_report(
            service_name=service_name,
            status=HealthStatus.UNHEALTHY,
            uptime=time.time(),
            last_error=datetime.now(timezone.utc),
            details={"error": str(e), "table": table},
        )


def register_collector_health_checks() -> None:
    register_health_check("Flashscore Discovery", _check_flashscore_discovery)
    register_health_check("Betting Discovery", _check_betting_discovery)
    register_health_check("Player Collector", _check_player_collector)
    register_health_check("Match Registry", _check_match_registry)
    register_health_check("Live Collector", _check_live_collector)
    register_health_check("Match Finalizer", _check_match_finalizer)
