from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from console_api.deps import get_db, pagination_params
from console_api.models import PaginatedResponse

router = APIRouter()


@router.get("/matching/summary")
def matching_summary(db: Session = Depends(get_db)):
    from models.tracked_match import TrackedMatch

    total = db.query(TrackedMatch).count()
    with_market = db.query(TrackedMatch).filter(
        TrackedMatch.betting_market_id.isnot(None)
    ).count()
    without_market = total - with_market
    matching_pct = round(with_market / total * 100, 1) if total else 0.0

    by_confidence = {}
    try:
        from matcher.models import MatchAttempt
        rows = (
            db.query(MatchAttempt.confidence_level, func.count())
            .filter(MatchAttempt.selected.is_(True))
            .group_by(MatchAttempt.confidence_level)
            .all()
        )
        by_confidence = {r[0]: r[1] for r in rows}
    except Exception:
        pass

    return {
        "total_tracked": total,
        "with_market": with_market,
        "without_market": without_market,
        "matching_pct": matching_pct,
        "by_confidence": by_confidence,
    }


@router.get("/matching/attempts", response_model=PaginatedResponse)
def matching_attempts(
    db: Session = Depends(get_db),
    pagination: dict = Depends(pagination_params),
    flashscore_match_id: str | None = Query(None),
    selected: bool | None = Query(None),
    rejected: bool | None = Query(None),
    confidence_level: str | None = Query(None),
):
    from matcher.models import MatchAttempt

    q = db.query(MatchAttempt)

    if flashscore_match_id:
        q = q.filter(MatchAttempt.flashscore_match_id == flashscore_match_id)
    if selected is not None:
        q = q.filter(MatchAttempt.selected.is_(selected))
    if rejected is not None:
        q = q.filter(MatchAttempt.rejected.is_(rejected))
    if confidence_level:
        q = q.filter(MatchAttempt.confidence_level == confidence_level)

    total = q.count()
    items = (
        q.order_by(MatchAttempt.created_at.desc())
        .offset(pagination["offset"])
        .limit(pagination["page_size"])
        .all()
    )

    return PaginatedResponse(
        items=[
            {
                "id": r.id,
                "flashscore_match_id": r.flashscore_match_id,
                "betting_market_id": r.betting_market_id,
                "player1_name": r.player1_name,
                "player2_name": r.player2_name,
                "tournament": r.tournament,
                "confidence_score": r.confidence_score,
                "confidence_level": r.confidence_level,
                "signal_scores": r.signal_scores,
                "signal_reasons": r.signal_reasons,
                "selected": r.selected,
                "rejected": r.rejected,
                "rejection_reason": r.rejection_reason,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in items
        ],
        total=total,
        page=pagination["page"],
        page_size=pagination["page_size"],
        total_pages=(total + pagination["page_size"] - 1) // pagination["page_size"] if pagination["page_size"] else 0,
    )


@router.get("/matching/unmatched")
def matching_unmatched(
    db: Session = Depends(get_db),
    limit: int = Query(200, le=1000),
    offset: int = Query(0, ge=0),
):
    from models.tracked_match import TrackedMatch

    q = db.query(TrackedMatch).filter(TrackedMatch.betting_market_id.is_(None))
    total = q.count()
    rows = q.order_by(TrackedMatch.id.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "matches": [
            {
                "id": r.id,
                "flashscore_match_id": r.flashscore_match_id,
                "player1_name": r.player1_name,
                "player2_name": r.player2_name,
                "tournament": r.tournament,
                "status": r.status,
                "scheduled_start": r.scheduled_start.isoformat() if r.scheduled_start else None,
            }
            for r in rows
        ],
    }
