from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from console_api.deps import get_db

router = APIRouter()


@router.get("/pipeline/status")
def pipeline_status(db: Session = Depends(get_db)):
    from models.system_event import SystemEvent

    last_se = (
        db.query(SystemEvent)
        .order_by(SystemEvent.timestamp.desc())
        .first()
    )

    def _last_run(source: str, pattern: str) -> str | None:
        row = (
            db.query(SystemEvent.timestamp)
            .filter(
                SystemEvent.source == source,
                SystemEvent.message.ilike(f"%{pattern}%"),
            )
            .order_by(SystemEvent.timestamp.desc())
            .first()
        )
        return row[0].isoformat() if row and row[0] else None

    discovery_last = _last_run("orchestrator", "discovery cycle") or _last_run("discovery", "completed")
    registry_last = _last_run("registry", "refresh") or _last_run("registry", "match")
    matching_last = _last_run("matcher", "match") or _last_run("matcher", "run")
    finalizer_last = _last_run("finalizer", "finalize") or _last_run("finalizer", "completed")
    repair_last = _last_run("repair", "repair") or _last_run("repair", "scan")

    # Collector heartbeat
    collector_stale = False
    latest_collector = db.execute(
        text("SELECT MAX(timestamp) FROM live_scores")
    ).scalar()
    if latest_collector:
        stale_seconds = (datetime.now(timezone.utc) - latest_collector).total_seconds()
        if stale_seconds > 3600:
            collector_stale = True

    from database import check_connection

    stages = [
        {
            "name": "Discovery",
            "status": "active" if discovery_last else "unknown",
            "last_run": discovery_last,
        },
        {
            "name": "Registry",
            "status": "active" if registry_last else "unknown",
            "last_run": registry_last,
        },
        {
            "name": "Market Matching",
            "status": "active" if matching_last else "unknown",
            "last_run": matching_last,
        },
        {
            "name": "Collectors",
            "status": "stale" if collector_stale else "active",
            "last_run": latest_collector.isoformat() if latest_collector else None,
        },
        {
            "name": "Database",
            "status": "healthy" if check_connection() else "unhealthy",
            "last_run": None,
        },
        {
            "name": "Finalizer",
            "status": "active" if finalizer_last else "unknown",
            "last_run": finalizer_last,
        },
        {
            "name": "Repair",
            "status": "active" if repair_last else "unknown",
            "last_run": repair_last,
        },
        {
            "name": "Completed",
            "status": "active",
            "last_run": last_se.timestamp.isoformat() if last_se else None,
        },
    ]

    return {"stages": stages}
