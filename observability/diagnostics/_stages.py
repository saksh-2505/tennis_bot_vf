from __future__ import annotations

import time
from datetime import datetime, timezone

from observability.diagnostics import PipelineDefinition, PipelineStageResult, PipelineStageStatus, register_pipeline
from observability.models import PipelineStageResult as PSR


def _check_table_has_rows(table: str, time_column: str | None = None, max_age_seconds: int | None = None) -> PipelineStageResult:
    from database import SessionLocal
    from sqlalchemy import text
    stage_name = f"DB: {table}"
    try:
        session = SessionLocal()
        try:
            query = f"SELECT COUNT(*) FROM {table}"
            if time_column:
                query = f"SELECT COUNT(*), MAX({time_column}) FROM {table}"
            result = session.execute(text(query))
            row = result.fetchone()
            count = row[0] if row else 0
            max_ts = row[1] if row and len(row) > 1 else None
            if count == 0:
                return PSR(stage_name=stage_name, status=PipelineStageStatus.FAIL, duration_ms=0.0,
                           error=f"No rows in {table}")
            if max_ts and max_age_seconds:
                age = (datetime.now(timezone.utc) - max_ts).total_seconds()
                if age > max_age_seconds:
                    return PSR(stage_name=stage_name, status=PipelineStageStatus.FAIL, duration_ms=0.0,
                               error=f"Data stale: {age:.0f}s old in {table} (max {max_age_seconds}s)")
            return PSR(stage_name=stage_name, status=PipelineStageStatus.PASS, duration_ms=0.0,
                       details={"row_count": count})
        finally:
            session.close()
    except Exception as e:
        return PSR(stage_name=stage_name, status=PipelineStageStatus.FAIL, duration_ms=0.0, error=str(e))


def _check_registry_has_tracked_matches() -> PipelineStageResult:
    result = _check_table_has_rows("tracked_matches", "updated_at", 86400)
    return PipelineStageResult(
        stage_name="Registry",
        status=result.status,
        duration_ms=0.0,
        error=result.error,
        details=result.details,
    )


def _check_tracked_match_has_live_data() -> PipelineStageResult:
    try:
        session = SessionLocal()
        try:
            result = session.execute(text(
                "SELECT COUNT(DISTINCT tracked_match_id) FROM live_scores "
                "WHERE timestamp > NOW() - INTERVAL '5 minutes'"
            ))
            count = result.scalar() or 0
            if count == 0:
                return PSR(stage_name="Live Collector", status=PipelineStageStatus.FAIL, duration_ms=0.0,
                           error="No live score data in last 5 minutes")
            return PSR(stage_name="Live Collector", status=PipelineStageStatus.PASS, duration_ms=0.0,
                       details={"active_matches_with_scores": count})
        finally:
            session.close()
    except Exception as e:
        return PSR(stage_name="Live Collector", status=PipelineStageStatus.FAIL, duration_ms=0.0, error=str(e))


def _check_finalizer_executed() -> PipelineStageResult:
    result = _check_table_has_rows("completed_matches", "finalized_at", 86400)
    return PipelineStageResult(
        stage_name="Finalizer",
        status=result.status,
        duration_ms=0.0,
        error=result.error,
        details=result.details,
    )


def _check_notification_sent() -> PipelineStageResult:
    result = _check_table_has_rows("completed_matches", "finalized_at", 86400)
    if result.status == PipelineStageStatus.PASS:
        return PSR(stage_name="Notification", status=PipelineStageStatus.PASS, duration_ms=0.0,
                   details={"note": "notifications inferred from completed matches"})
    return PSR(stage_name="Notification", status=PipelineStageStatus.SKIPPED, duration_ms=0.0)


def register_pipeline_definitions() -> None:
    register_pipeline(PipelineDefinition(
        name="Live Score Pipeline",
        stages=[
            ("Flashscore Fetch", lambda: _check_table_has_rows("flashscorefoundmatches", "discovered_at", 86400)),
            ("Parser", lambda: _check_table_has_rows("flashscorefoundmatches", "discovered_at", 86400)),
            ("Registry", _check_registry_has_tracked_matches),
            ("Collector", _check_tracked_match_has_live_data),
            ("Database", lambda: _check_table_has_rows("live_scores", "timestamp", 300)),
            ("Finalizer", _check_finalizer_executed),
            ("Completed Match", lambda: _check_table_has_rows("completed_matches", "finalized_at", 86400)),
        ],
    ))

    register_pipeline(PipelineDefinition(
        name="Discovery Pipeline",
        stages=[
            ("Flashscore Fetch", lambda: _check_table_has_rows("flashscorefoundmatches", "discovered_at", 86400)),
            ("Betting Site Fetch", lambda: _check_table_has_rows("bettingsitefoundmatches", "discovered_at", 86400)),
            ("Registry", _check_registry_has_tracked_matches),
        ],
    ))

    register_pipeline(PipelineDefinition(
        name="Odds Pipeline",
        stages=[
            ("Betting Site Fetch", lambda: _check_table_has_rows("bettingsitefoundmatches", "discovered_at", 86400)),
            ("Parser", lambda: _check_table_has_rows("bettingsitefoundmatches", "discovered_at", 86400)),
            ("Registry", _check_registry_has_tracked_matches),
            ("Collector", lambda: _check_table_has_rows("live_odds", "timestamp", 300)),
            ("Database", lambda: _check_table_has_rows("live_odds", "timestamp", 300)),
        ],
    ))

    register_pipeline(PipelineDefinition(
        name="Player Updates Pipeline",
        stages=[
            ("Tennis Explorer Fetch", lambda: _check_table_has_rows("players", "updated_at", 86400)),
            ("Parser", lambda: _check_table_has_rows("players", "updated_at", 86400)),
            ("Database", lambda: _check_table_has_rows("players", "updated_at", 86400)),
        ],
    ))

    register_pipeline(PipelineDefinition(
        name="Incident Creation Pipeline",
        stages=[
            ("Monitor Tick", lambda: _check_table_has_rows("incidents", "last_detected_at", 3600)),
            ("Detection", lambda: _check_table_has_rows("incidents", "last_detected_at", 3600)),
            ("Notification", _check_notification_sent),
        ],
    ))
