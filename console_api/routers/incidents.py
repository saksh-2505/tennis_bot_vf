from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from console_api.deps import get_db, pagination_params
from console_api.models import IncidentSummary, PaginatedResponse

router = APIRouter()


@router.get("/incidents", response_model=PaginatedResponse)
def get_incidents(
    db: Session = Depends(get_db),
    pagination: dict = Depends(pagination_params),
    status: str | None = Query(None),
    severity: str | None = Query(None),
    category: str | None = Query(None),
    tracked_match_id: int | None = Query(None),
):
    from incidents.models import Incident

    q = db.query(Incident)

    if status:
        q = q.filter(Incident.status == status.upper())
    if severity:
        q = q.filter(Incident.severity == severity.upper())
    if category:
        q = q.filter(Incident.category.ilike(f"%{category}%"))
    if tracked_match_id is not None:
        q = q.filter(Incident.tracked_match_id == tracked_match_id)

    total = q.count()
    rows = (
        q.order_by(Incident.last_detected_at.desc())
        .offset(pagination["offset"])
        .limit(pagination["page_size"])
        .all()
    )

    return PaginatedResponse(
        items=[
            IncidentSummary(
                id=r.incident_id,
                severity=r.severity,
                status=r.status,
                category=r.category,
                module=r.module,
                title=r.title,
                first_detected=r.first_detected_at,
                occurrence_count=r.occurrence_count,
                tracked_match_id=r.tracked_match_id,
            ).model_dump()
            for r in rows
        ],
        total=total,
        page=pagination["page"],
        page_size=pagination["page_size"],
        total_pages=(total + pagination["page_size"] - 1) // pagination["page_size"] if pagination["page_size"] else 0,
    )


@router.get("/incidents/{incident_id}")
def get_incident_detail(incident_id: int, db: Session = Depends(get_db)):
    from incidents.models import Incident

    r = db.get(Incident, incident_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    return {
        "id": r.incident_id,
        "severity": r.severity,
        "status": r.status,
        "category": r.category,
        "module": r.module,
        "tracked_match_id": r.tracked_match_id,
        "collector_name": r.collector_name,
        "title": r.title,
        "summary": r.summary,
        "incident_hash": r.incident_hash,
        # Field name parity with IncidentSummary / `TS IncidentDetail extends IncidentSummary`.
        "first_detected": r.first_detected_at.isoformat() if r.first_detected_at else None,
        "last_detected_at": r.last_detected_at.isoformat() if r.last_detected_at else None,
        "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        "occurrence_count": r.occurrence_count,
        "recovery_attempts": r.recovery_attempts,
    }
