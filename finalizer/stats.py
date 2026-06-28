import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func

from models.live_odds import LiveOdds
from models.live_score import LiveScore

logger = logging.getLogger(__name__)


@dataclass
class MatchStats:
    score_tick_count: int = 0
    odds_tick_count: int = 0
    first_score_timestamp: datetime | None = None
    last_score_timestamp: datetime | None = None
    first_odds_timestamp: datetime | None = None
    last_odds_timestamp: datetime | None = None
    score_collection_duration_seconds: int | None = None
    odds_collection_duration_seconds: int | None = None
    duplicate_score_ticks: int = 0
    duplicate_odds_ticks: int = 0
    largest_score_gap_seconds: float | None = None
    largest_odds_gap_seconds: float | None = None


def _compute_duplicates(session, model, match_id_col: str, match_id: int) -> int:
    table = model.__tablename__
    stmt = (
        session.query(func.count())
        .select_from(model)
        .filter(getattr(model, match_id_col) == match_id)
        .group_by(model.content_hash)
        .having(func.count() > 1)
    )
    duplicates = stmt.all()
    return len(duplicates)


def _largest_gap(timestamps: list[datetime]) -> float | None:
    if len(timestamps) < 2:
        return None
    gaps = [
        (timestamps[i + 1] - timestamps[i]).total_seconds()
        for i in range(len(timestamps) - 1)
    ]
    return max(gaps) if gaps else None


def calculate_stats(session, tracked_match_id: int) -> MatchStats:
    stats = MatchStats()

    scores = (
        session.query(LiveScore)
        .filter(LiveScore.tracked_match_id == tracked_match_id)
        .order_by(LiveScore.timestamp.asc())
        .all()
    )
    odds = (
        session.query(LiveOdds)
        .filter(LiveOdds.tracked_match_id == tracked_match_id)
        .order_by(LiveOdds.timestamp.asc())
        .all()
    )

    stats.score_tick_count = len(scores)
    stats.odds_tick_count = len(odds)

    if scores:
        stats.first_score_timestamp = scores[0].timestamp
        stats.last_score_timestamp = scores[-1].timestamp
        delta = scores[-1].timestamp - scores[0].timestamp
        stats.score_collection_duration_seconds = int(
            delta.total_seconds()
        )
        stats.largest_score_gap_seconds = _largest_gap(
            [s.timestamp for s in scores]
        )

    if odds:
        stats.first_odds_timestamp = odds[0].timestamp
        stats.last_odds_timestamp = odds[-1].timestamp
        delta = odds[-1].timestamp - odds[0].timestamp
        stats.odds_collection_duration_seconds = int(
            delta.total_seconds()
        )
        stats.largest_odds_gap_seconds = _largest_gap(
            [o.timestamp for o in odds]
        )

    stats.duplicate_score_ticks = _compute_duplicates(
        session, LiveScore, "tracked_match_id", tracked_match_id
    )
    stats.duplicate_odds_ticks = _compute_duplicates(
        session, LiveOdds, "tracked_match_id", tracked_match_id
    )

    return stats
