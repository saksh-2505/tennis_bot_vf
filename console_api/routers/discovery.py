from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from console_api.deps import get_db

router = APIRouter()


@router.get("/discovery/summary")
def discovery_summary(db: Session = Depends(get_db)):
    flashscore_by_day = db.execute(
        text(
            "SELECT discovered_at::date AS day, COUNT(*) "
            "FROM flashscorefoundmatches "
            "GROUP BY discovered_at::date "
            "ORDER BY day DESC LIMIT 90"
        )
    ).fetchall()

    bettingsite_by_day = db.execute(
        text(
            "SELECT discovered_at::date AS day, COUNT(*) "
            "FROM bettingsitefoundmatches "
            "GROUP BY discovered_at::date "
            "ORDER BY day DESC LIMIT 90"
        )
    ).fetchall()

    flashscore_total = db.execute(text("SELECT COUNT(*) FROM flashscorefoundmatches")).scalar() or 0
    bettingsite_total = db.execute(text("SELECT COUNT(*) FROM bettingsitefoundmatches")).scalar() or 0

    return {
        "flashscore_total": flashscore_total,
        "bettingsite_total": bettingsite_total,
        "flashscore_by_day": [
            {"date": str(r[0]), "count": r[1]} for r in flashscore_by_day
        ],
        "bettingsite_by_day": [
            {"date": str(r[0]), "count": r[1]} for r in bettingsite_by_day
        ],
    }


@router.get("/discovery/runs")
def discovery_runs(
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
):
    from models.system_event import SystemEvent

    rows = (
        db.query(SystemEvent)
        .filter(
            SystemEvent.source == "orchestrator",
            SystemEvent.message.ilike("%discovery cycle%"),
        )
        .order_by(SystemEvent.timestamp.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "level": r.level,
            "source": r.source,
            "message": r.message,
            "details": r.details,
        }
        for r in rows
    ]
