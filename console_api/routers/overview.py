"""Overview API — platform health and summary statistics."""
import time
from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from console_api.deps import get_db
from console_api.models import PlatformOverview

router = APIRouter()

# Simple module-level TTL cache — avoids the unhashable-Session problem of
# wrapping functools.lru_cache on a function that receives a Session.
_cache = {"data": None, "expires": 0.0}


def _compute_overview(db: Session) -> PlatformOverview:
    from models.tracked_match import TrackedMatch
    from models.completed_match import CompletedMatch
    from models.player import Player
    from incidents.models import Incident

    tracked_agg = (
        db.query(
            func.count().label("total"),
            func.count().filter(TrackedMatch.status == "LIVE").label("live"),
            func.count().filter(
                TrackedMatch.status.in_(["DISCOVERED", "SCHEDULED"])
            ).label("scheduled"),
            func.count().filter(TrackedMatch.status == "FINISHED").label("finished"),
        )
        .first()
    )
    total_players = db.query(Player).count()
    total_incidents = db.query(Incident).count()
    open_incidents = (
        db.query(Incident)
        .filter(Incident.status.in_(["OPEN", "ACKNOWLEDGED", "RECOVERING"]))
        .count()
    )

    cm_agg = (
        db.query(
            func.count().label("total"),
            func.count().filter(CompletedMatch.validation_passed.is_(True)).label("validation_pass"),
            func.count().filter(CompletedMatch.odds_tick_count > 0).label("with_odds"),
            func.count().filter(CompletedMatch.ready_for_replay.is_(True)).label("replay_ready"),
            func.avg(CompletedMatch.quality_score).filter(
                CompletedMatch.quality_score.isnot(None)
            ).label("avg_quality"),
        )
        .first()
    )

    # TimescaleDB ≥2.0: `approximate_row_count(regclass)` in public schema.
    # Falls back to a real COUNT(*) if the function is missing or older.
    def _approx(table: str) -> int:
        try:
            return (
                db.execute(text("SELECT approximate_row_count(:tbl)"), {"tbl": table}).scalar()
                or 0
            )
        except Exception:
            return db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0

    score_ticks = _approx("live_scores")
    odds_ticks = _approx("live_odds")

    tc = cm_agg.total
    return PlatformOverview(
        total_matches=tracked_agg.total,
        live_matches=tracked_agg.live,
        scheduled_matches=tracked_agg.scheduled,
        finished_matches=tracked_agg.finished,
        total_players=total_players,
        total_incidents=total_incidents,
        open_incidents=open_incidents,
        total_score_ticks=score_ticks,
        total_odds_ticks=odds_ticks,
        validation_pass_pct=round(cm_agg.validation_pass / tc * 100, 1) if tc else 0,
        odds_coverage_pct=round(cm_agg.with_odds / tc * 100, 1) if tc else 0,
        replay_ready_pct=round(cm_agg.replay_ready / tc * 100, 1) if tc else 0,
        avg_quality_score=round(cm_agg.avg_quality, 1) if cm_agg.avg_quality else None,
    )


@router.get("/overview", response_model=PlatformOverview)
def get_overview(db: Session = Depends(get_db)):
    now = time.monotonic()
    if _cache["data"] is not None and now < _cache["expires"]:
        return _cache["data"]
    result = _compute_overview(db)
    _cache["data"] = result
    _cache["expires"] = now + 15
    return result
