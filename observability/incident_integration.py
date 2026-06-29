from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from observability.health import get_all_health, get_platform_health_summary
from observability.metrics import get_metrics
from observability.service_monitor import get_service_monitor
from observability.tracing import get_trace


def build_diagnostic_context(
    incident_id: int | None = None,
    tracked_match_id: int | None = None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    context["health_snapshot"] = get_platform_health_summary()
    context["current_metrics"] = get_metrics().snapshot()
    context["service_status"] = get_service_monitor().service_summary()
    context["collector_status"] = _get_collector_status()
    context["database_status"] = _get_database_status()
    context["environment"] = _get_environment_info()

    if tracked_match_id:
        context["match_context"] = _get_match_context(tracked_match_id)

    return context


def _get_collector_status() -> dict[str, Any]:
    try:
        from database import SessionLocal
        from sqlalchemy import text
        session = SessionLocal()
        try:
            result: dict[str, Any] = {}
            queries = {
                "flashscore_match_count": "SELECT COUNT(*) FROM flashscorefoundmatches",
                "bettingsite_match_count": "SELECT COUNT(*) FROM bettingsitefoundmatches",
                "tracked_match_count": "SELECT COUNT(*) FROM tracked_matches",
                "live_score_count": "SELECT COUNT(*) FROM live_scores WHERE timestamp > NOW() - INTERVAL '1 hour'",
                "live_odds_count": "SELECT COUNT(*) FROM live_odds WHERE timestamp > NOW() - INTERVAL '1 hour'",
                "completed_match_count": "SELECT COUNT(*) FROM completed_matches",
                "incident_count": "SELECT COUNT(*) FROM incidents WHERE status = 'OPEN'",
            }
            for key, query in queries.items():
                row = session.execute(text(query)).fetchone()
                result[key] = row[0] if row else 0
            return result
        finally:
            session.close()
    except Exception as e:
        return {"error": str(e)}


def _get_database_status() -> dict[str, Any]:
    try:
        from database import SessionLocal
        from sqlalchemy import text
        session = SessionLocal()
        try:
            result = session.execute(text(
                "SELECT schemaname, tablename, n_live_tup, n_dead_tup, "
                "last_autovacuum, last_analyze "
                "FROM pg_stat_user_tables ORDER BY n_live_tup DESC"
            )).fetchall()
            tables = []
            for r in result:
                tables.append({
                    "table": f"{r[0]}.{r[1]}",
                    "live_rows": r[2],
                    "dead_rows": r[3],
                    "last_autovacuum": r[4].isoformat() if r[4] else None,
                    "last_analyze": r[5].isoformat() if r[5] else None,
                })
            return {"tables": tables}
        finally:
            session.close()
    except Exception as e:
        return {"error": str(e)}


def _get_environment_info() -> dict[str, Any]:
    import os
    import sys
    return {
        "python_version": sys.version,
        "platform": sys.platform,
        "cwd": os.getcwd(),
        "pid": os.getpid(),
    }


def _get_match_context(tracked_match_id: int) -> dict[str, Any] | None:
    try:
        from database import SessionLocal
        from sqlalchemy import text
        session = SessionLocal()
        try:
            match = session.execute(text(
                "SELECT id, status, flashscore_match_id, betting_market_id, "
                "player1_name, player2_name, tournament, scheduled_start, "
                "tracking_enabled, created_at, updated_at "
                "FROM tracked_matches WHERE id = :mid",
                {"mid": tracked_match_id},
            )).fetchone()
            if match is None:
                return None
            return {
                "id": match[0],
                "status": match[1],
                "flashscore_match_id": match[2],
                "betting_market_id": match[3],
                "players": f"{match[4]} vs {match[5]}",
                "tournament": match[6],
                "scheduled_start": match[7].isoformat() if match[7] else None,
                "tracking_enabled": match[8],
            }
        finally:
            session.close()
    except Exception:
        return None


def enhance_incident_package(
    package_dir: str,
    incident_id: int | None = None,
    tracked_match_id: int | None = None,
) -> str:
    import os
    context = build_diagnostic_context(incident_id, tracked_match_id)
    diagnostics_path = os.path.join(package_dir, "observability_context.json")
    with open(diagnostics_path, "w") as f:
        json.dump(context, f, indent=2, default=str)
    return diagnostics_path
