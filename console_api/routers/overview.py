"""Overview API — platform health and summary statistics."""
from functools import lru_cache
import time
from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from console_api.deps import get_db
from console_api.models import PlatformOverview

router = APIRouter()


def _cached(ttl_seconds: int):
    """Simple TTL cache wrapper for lru_cache(maxsize=1) — 1-item cache with TTL expiry."""
    def decorator(f):
        memo = {"value": None, "expires": 0.0}
        @lru_cache(maxsize=1)
        def _inner(*args, **kwargs):
            now = time.monotonic()
            if now < memo["expires"] and memo["value"] is not None:
                return memo["value"]
            result = f(*args, **kwargs)
            memo["value"] = result
            memo["expires"] = now + ttl_seconds
            return result
        return _inner
    return decorator


@_cached(ttl_seconds=15)
def _overview_counts(db: Session):
    """Folded count queries — one round-trip for tracked_matches + completed_matches.

    Hypertable row counts use TimescaleDB's approximate_row_count() which
    samples internal chunk-level stats instead of scanning 53k/228k rows."""
    from models.tracked_match import TrackedMatch
    from models.completed_match import CompletedMatch
    from models.player import Player
    from incidents.models import Incident

    # Single folded query for the counted subsets of tracked_matches.
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

    # Completed-match aggregates — folded into one query.
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

    # Approximate hypertable row counts (avoids full scans over 53k/228k rows).
    score_ticks = (
        db.execute(
            text("SELECT _timescaledb_internal.approximate_row_count('live_scores')")
        ).scalar()
        or 0
    )
    odds_ticks = (
        db.execute(
            text("SELECT _timescaledb_internal.approximate_row_count('live_odds')")
        ).scalar()
        or 0
    )

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
    return _overview_counts(db)
