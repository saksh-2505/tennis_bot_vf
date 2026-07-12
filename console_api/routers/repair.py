from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from console_api.deps import get_db

router = APIRouter()


@router.get("/repairs/summary")
def repairs_summary(db: Session = Depends(get_db)):
    from models.completed_match import CompletedMatch

    repaired_total = db.query(CompletedMatch).filter(
        CompletedMatch.repair_count > 0
    ).count()

    actions_q = (
        db.query(
            CompletedMatch.repair_actions,
            func.count(),
        )
        .filter(
            CompletedMatch.repair_count > 0,
            CompletedMatch.repair_actions.isnot(None),
        )
        .group_by(CompletedMatch.repair_actions)
        .all()
    )

    return {
        "total_repaired": repaired_total,
        "by_repair_action": [
            {"action": a or "unknown", "count": c}
            for a, c in actions_q
        ],
    }


@router.get("/repairs/history")
def repairs_history(
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    from models.completed_match import CompletedMatch

    q = db.query(CompletedMatch).filter(CompletedMatch.repair_count > 0)
    total = q.count()
    rows = (
        q.order_by(CompletedMatch.last_repaired_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "repairs": [
            {
                "tracked_match_id": r.tracked_match_id,
                "flashscore_match_id": r.flashscore_match_id,
                "tournament": r.tournament,
                "repair_actions": r.repair_actions,
                "repair_count": r.repair_count,
                "last_repaired_at": r.last_repaired_at.isoformat() if r.last_repaired_at else None,
                "quality_grade": r.quality_grade,
                "validation_passed": r.validation_passed,
            }
            for r in rows
        ],
    }
