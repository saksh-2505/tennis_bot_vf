from __future__ import annotations

from typing import Any

from observability.diagnostics import validate_pipeline, validate_platform
from observability.health import get_health, get_all_health, get_platform_health_summary
# get_match_monitor imported lazily in validate_match_pipeline
from observability.metrics import get_metrics
from observability.telegram_diagnostics import get_telegram_diagnostics
from observability.tracing import get_trace


def get_platform_health() -> dict[str, Any]:
    return get_platform_health_summary()


def get_service_health(service: str) -> dict[str, Any] | None:
    report = get_health(service)
    if report is None:
        return None
    return {
        "service_name": report.service_name,
        "status": report.status.value,
        "uptime": report.uptime,
        "last_success": report.last_success.isoformat() if report.last_success else None,
        "last_error": report.last_error.isoformat() if report.last_error else None,
        "heartbeat_time": report.heartbeat_time.isoformat() if report.heartbeat_time else None,
        "active_tasks": report.active_tasks,
        "processed_items": report.processed_items,
        "average_latency_ms": report.average_latency_ms,
        "cpu_usage": report.cpu_usage,
        "memory_usage": report.memory_usage,
        "details": report.details,
    }


def get_trace_view(trace_id: str) -> dict[str, Any] | None:
    trace = get_trace(trace_id)
    if trace is None:
        return None
    return {
        "trace_id": trace.trace_id,
        "started_at": trace.started_at.isoformat(),
        "ended_at": trace.ended_at.isoformat() if trace.ended_at else None,
        "root_operation": trace.root_operation,
        "spans": [
            {
                "span_id": s.span_id,
                "parent_span_id": s.parent_span_id,
                "operation": s.operation,
                "service": s.service,
                "module": s.module,
                "component": s.component,
                "started_at": s.started_at.isoformat(),
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "duration_ms": (
                    (s.ended_at - s.started_at).total_seconds() * 1000.0
                    if s.ended_at else None
                ),
                "status": s.status,
                "metadata": s.metadata,
            }
            for s in trace.spans
        ],
    }


def validate_platform_pipelines() -> dict[str, Any]:
    return {
        name: _serialize_pipeline_result(result)
        for name, result in validate_platform().items()
    }


def validate_named_pipeline(name: str) -> dict[str, Any] | None:
    result = validate_pipeline(name)
    if result is None:
        return None
    return _serialize_pipeline_result(result)


def validate_match_pipeline(match_id: int) -> dict[str, Any]:
    from observability.match_monitor import get_match_monitor
    return get_match_monitor().validate_match_pipeline(match_id)


def get_platform_metrics() -> dict[str, Any]:
    return get_metrics().snapshot()


def get_recent_telegram_diagnostics(limit: int = 50) -> list[dict[str, Any]]:
    return [
        {
            "stage": d.stage,
            "status": d.status.value,
            "duration_ms": d.duration_ms,
            "chat_id": d.chat_id,
            "http_status_code": d.http_status_code,
            "telegram_message_id": d.telegram_message_id,
            "error": d.error,
            "timestamp": d.timestamp.isoformat(),
        }
        for d in get_telegram_diagnostics(limit)
    ]


def get_recent_incidents() -> list[dict[str, Any]]:
    try:
        from database import SessionLocal
        from sqlalchemy import text
        session = SessionLocal()
        try:
            rows = session.execute(text(
                "SELECT incident_id, severity, status, category, module, title, "
                "summary, tracked_match_id, first_detected_at, last_detected_at, "
                "occurrence_count "
                "FROM incidents ORDER BY last_detected_at DESC LIMIT 50"
            )).fetchall()
            return [
                {
                    "incident_id": r[0],
                    "severity": r[1],
                    "status": r[2],
                    "category": r[3],
                    "module": r[4],
                    "title": r[5],
                    "summary": r[6],
                    "tracked_match_id": r[7],
                    "first_detected_at": r[8].isoformat() if r[8] else None,
                    "last_detected_at": r[9].isoformat() if r[9] else None,
                    "occurrence_count": r[10],
                }
                for r in rows
            ]
        finally:
            session.close()
    except Exception:
        return []


def _serialize_pipeline_result(result: Any) -> dict[str, Any]:
    return {
        "pipeline_name": result.pipeline_name,
        "overall_status": result.overall_status.value,
        "first_failure": result.first_failure,
        "started_at": result.started_at.isoformat(),
        "ended_at": result.ended_at.isoformat(),
        "stages": [
            {
                "stage_name": s.stage_name,
                "status": s.status.value,
                "duration_ms": s.duration_ms,
                "error": s.error,
                "details": s.details,
            }
            for s in result.stages
        ],
    }
