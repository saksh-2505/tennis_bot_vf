from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from console_api.deps import get_db, pagination_params
from console_api.models import PaginatedResponse

router = APIRouter()


@router.get("/registry/summary")
def registry_summary(db: Session = Depends(get_db)):
    from models.tracked_match import TrackedMatch

    rows = (
        db.query(TrackedMatch.status, func.count())
        .group_by(TrackedMatch.status)
        .all()
    )

    by_status = {r[0]: r[1] for r in rows}

    return {
        "total": db.query(TrackedMatch).count(),
        "by_status": by_status,
    }


@router.get("/registry/players", response_model=PaginatedResponse)
def registry_players(
    db: Session = Depends(get_db),
    pagination: dict = Depends(pagination_params),
):
    from models.player import Player

    total = db.query(Player).count()
    rows = (
        db.query(Player)
        .order_by(Player.full_name)
        .offset(pagination["offset"])
        .limit(pagination["page_size"])
        .all()
    )

    return PaginatedResponse(
        items=[
            {
                "player_id": p.player_id,
                "full_name": p.full_name,
                "nationality": p.nationality,
                "age": p.age,
                "gender": p.gender,
                "atp_or_wta": p.atp_or_wta,
                "current_rank": p.current_rank,
                "career_high_rank": p.career_high_rank,
                "total_matches": p.total_matches,
                "total_wins": p.total_wins,
                "total_losses": p.total_losses,
                "career_win_percentage": p.career_win_percentage,
                "plays": p.plays,
                "backhand": p.backhand,
            }
            for p in rows
        ],
        total=total,
        page=pagination["page"],
        page_size=pagination["page_size"],
        total_pages=(total + pagination["page_size"] - 1) // pagination["page_size"] if pagination["page_size"] else 0,
    )
