from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from console_api.deps import get_db

router = APIRouter()


@router.get("/observability/health")
def observability_health(db: Session = Depends(get_db)):
    from database import check_connection
    db_ok = check_connection()
    return {"db": db_ok, "version": "4.0.0"}


@router.get("/observability/metrics")
def observability_metrics(db: Session = Depends(get_db)):
    from models.system_event import SystemEvent

    by_level = (
        db.query(SystemEvent.level, func.count())
        .group_by(SystemEvent.level)
        .all()
    )

    by_source = (
        db.query(SystemEvent.source, func.count())
        .group_by(SystemEvent.source)
        .all()
    )

    recent = (
        db.query(SystemEvent)
        .order_by(SystemEvent.timestamp.desc())
        .limit(50)
        .all()
    )

    return {
        "events_by_level": {r[0]: r[1] for r in by_level},
        "events_by_source": {r[0]: r[1] for r in by_source},
        "recent_events": [
            {
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "level": e.level,
                "source": e.source,
                "message": e.message,
            }
            for e in recent
        ],
    }
