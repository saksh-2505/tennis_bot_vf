from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from console_api.deps import get_db, pagination_params
from console_api.models import PaginatedResponse

router = APIRouter()


@router.get("/timeline", response_model=PaginatedResponse)
def get_timeline(
    db: Session = Depends(get_db),
    pagination: dict = Depends(pagination_params),
    source: str | None = Query(None),
    level: str | None = Query(None),
    tracked_match_id: int | None = Query(None),
):
    from models.system_event import SystemEvent

    q = db.query(SystemEvent)

    if source:
        q = q.filter(SystemEvent.source == source)
    if level:
        q = q.filter(SystemEvent.level == level.upper())
    if tracked_match_id is not None:
        q = q.filter(SystemEvent.tracked_match_id == tracked_match_id)

    total = q.count()
    rows = (
        q.order_by(SystemEvent.timestamp.desc())
        .offset(pagination["offset"])
        .limit(pagination["page_size"])
        .all()
    )

    return PaginatedResponse(
        items=[
            {
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "event_id": r.event_id,
                "level": r.level,
                "source": r.source,
                "message": r.message,
                "details": r.details,
                "incident_id": r.incident_id,
                "tracked_match_id": r.tracked_match_id,
            }
            for r in rows
        ],
        total=total,
        page=pagination["page"],
        page_size=pagination["page_size"],
        total_pages=(total + pagination["page_size"] - 1) // pagination["page_size"] if pagination["page_size"] else 0,
    )
