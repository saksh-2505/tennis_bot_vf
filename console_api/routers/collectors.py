from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from console_api.deps import get_db

router = APIRouter()

COLLECTORS = [
    {"name": "flashscore", "table": "flashscorefoundmatches", "col": "discovered_at"},
    {"name": "bettingsite", "table": "bettingsitefoundmatches", "col": "discovered_at"},
    {"name": "live_score", "table": "live_scores", "col": "timestamp"},
    {"name": "live_odds", "table": "live_odds", "col": "timestamp"},
]


@router.get("/collectors")
def get_collectors(db: Session = Depends(get_db)):
    result = []
    for c in COLLECTORS:
        row = db.execute(
            text(f"SELECT MAX({c['col']}) AS last_ts, COUNT(*) AS cnt FROM {c['table']}")
        ).fetchone()
        last_ts = row[0] if row else None
        count = row[1] if row else 0

        heartbeat_seconds = None
        if last_ts:
            delta = datetime.now(timezone.utc) - last_ts
            heartbeat_seconds = round(delta.total_seconds(), 1)

        stale_threshold = 600
        if c["name"] in ("live_score", "live_odds"):
            stale_threshold = 3600  # these are event-driven, allow longer gaps

        if c["name"] == "system_events":
            # system_events is not part of this loop (handled separately below)
            pass

        status = "active"
        if heartbeat_seconds is None or heartbeat_seconds > stale_threshold:
            status = "stale"

        result.append({
            "name": c["name"],
            "status": status,
            "last_poll": last_ts.isoformat() if last_ts else None,
            "records_count": count,
            "heartbeat_seconds_ago": heartbeat_seconds,
        })

    se_row = db.execute(
        text("SELECT MAX(timestamp) AS last_ts, COUNT(*) AS cnt FROM system_events")
    ).fetchone()
    se_last = se_row[0] if se_row else None
    se_count = se_row[1] if se_row else 0
    se_heartbeat = None
    if se_last:
        se_heartbeat = round((datetime.now(timezone.utc) - se_last).total_seconds(), 1)

    result.append({
        "name": "system_events",
        "status": "active" if se_heartbeat and se_heartbeat < 600 else "stale",
        "last_poll": se_last.isoformat() if se_last else None,
        "records_count": se_count,
        "heartbeat_seconds_ago": se_heartbeat,
    })

    return result
