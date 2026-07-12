"""Overview API — platform health and summary statistics."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from console_api.deps import get_db
from console_api.models import PlatformOverview

router = APIRouter()


@router.get("/overview", response_model=PlatformOverview)
def get_overview(db: Session = Depends(get_db)):
    from models.tracked_match import TrackedMatch
    from models.completed_match import CompletedMatch
    from incidents.models import Incident

    total = db.query(TrackedMatch).count()
    live = db.query(TrackedMatch).filter(TrackedMatch.status == "LIVE").count()
    scheduled = db.query(TrackedMatch).filter(
        TrackedMatch.status.in_(["DISCOVERED", "SCHEDULED"])
    ).count()
    finished = db.query(TrackedMatch).filter(
        TrackedMatch.status == "FINISHED"
    ).count()

    from models.player import Player

    total_players = db.query(Player).count()

    total_incidents = db.query(Incident).count()
    open_incidents = db.query(Incident).filter(
        Incident.status.in_(["OPEN", "ACKNOWLEDGED", "RECOVERING"])
    ).count()

    score_ticks = db.execute(text("SELECT COUNT(*) FROM live_scores")).scalar() or 0
    odds_ticks = db.execute(text("SELECT COUNT(*) FROM live_odds")).scalar() or 0

    total_completed = db.query(CompletedMatch).count()
    if total_completed:
        validation_pass = db.query(CompletedMatch).filter(
            CompletedMatch.validation_passed.is_(True)
        ).count()
        with_odds = db.query(CompletedMatch).filter(
            CompletedMatch.odds_tick_count > 0
        ).count()
        replay_ready = db.query(CompletedMatch).filter(
            CompletedMatch.ready_for_replay.is_(True)
        ).count()
        avg_quality = db.query(func.avg(CompletedMatch.quality_score)).filter(
            CompletedMatch.quality_score.isnot(None)
        ).scalar()
    else:
        validation_pass = 0
        with_odds = 0
        replay_ready = 0
        avg_quality = None

    return PlatformOverview(
        total_matches=total,
        live_matches=live,
        scheduled_matches=scheduled,
        finished_matches=finished,
        total_players=total_players,
        total_incidents=total_incidents,
        open_incidents=open_incidents,
        total_score_ticks=score_ticks,
        total_odds_ticks=odds_ticks,
        validation_pass_pct=round(validation_pass / total_completed * 100, 1) if total_completed else 0,
        odds_coverage_pct=round(with_odds / total_completed * 100, 1) if total_completed else 0,
        replay_ready_pct=round(replay_ready / total_completed * 100, 1) if total_completed else 0,
        avg_quality_score=round(avg_quality, 1) if avg_quality else None,
    )
