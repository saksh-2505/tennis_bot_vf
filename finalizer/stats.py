"""Match statistics calculation: tick counts, gaps, duplicates, game states, odds-at-score coverage."""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, text

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
    unique_set_states: int = 0
    expected_set_states: int = 0
    odds_at_score_matched: int = 0
    odds_at_score_total: int = 0
    odds_at_score_pct: float = 0.0


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


def _parse_expected_set_states(final_set_score: str | None) -> int:
    """Calculate expected unique game-level (set_a, set_b) score states.

    For '6-4, 6-3': (6+4+1) + (6+3+1) = 21 unique states.
    For '6-4, 7-6': (6+4+1) + (7+6+1) = 29 unique states.
    Each state represents one distinct (set_score_a, set_score_b) pair.
    """
    if not final_set_score:
        return 0
    expected = 0
    for part in final_set_score.split(","):
        part = part.strip()
        scores = part.split("-")
        if len(scores) == 2:
            try:
                a = int(scores[0].strip())
                b = int(scores[1].strip())
                if a + b > 0:
                    expected += a + b + 1
            except ValueError:
                pass
    return expected


def _count_unique_set_states(session, tracked_match_id: int) -> int:
    """Count unique (set_score_a, set_score_b) pairs in live_scores.

    These represent game-level score transitions, not point-level.
    """
    from models.live_score import LiveScore

    result = (
        session.query(LiveScore.set_score_a, LiveScore.set_score_b)
        .filter(LiveScore.tracked_match_id == tracked_match_id)
        .distinct()
        .count()
    )
    return result or 0


def _odds_at_score_coverage(
    session, tracked_match_id: int, window_seconds: float = 5.0
) -> tuple[int, int, float]:
    """For each distinct score tick, check if an odds tick exists within window_seconds.

    Computes in Python to be database-agnostic (SQLite in tests, PostgreSQL in production).
    Returns (total_score_timestamps, matched_count, coverage_pct).
    """
    from models.live_score import LiveScore
    from models.live_odds import LiveOdds

    rows = (
        session.query(LiveScore.timestamp)
        .filter(LiveScore.tracked_match_id == tracked_match_id)
        .order_by(LiveScore.timestamp.asc())
        .all()
    )
    seen = set()
    score_times = []
    for r in rows:
        ts = r[0]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        key = ts.replace(microsecond=0)
        if key not in seen:
            seen.add(key)
            score_times.append(ts)
    if not score_times:
        return 0, 0, 0.0

    odds_rows = (
        session.query(LiveOdds.timestamp)
        .filter(LiveOdds.tracked_match_id == tracked_match_id)
        .order_by(LiveOdds.timestamp.asc())
        .all()
    )
    odds_times = [r[0] for r in odds_rows]

    total = len(score_times)
    matched = 0

    for st in score_times:
        if st.tzinfo is None:
            st = st.replace(tzinfo=timezone.utc)
        nearest_gap = float("inf")
        for ot in odds_times:
            if ot.tzinfo is None:
                ot = ot.replace(tzinfo=timezone.utc)
            gap = abs((st - ot).total_seconds())
            if gap < nearest_gap:
                nearest_gap = gap
        if nearest_gap <= window_seconds:
            matched += 1

    pct = round(matched / total * 100, 1) if total else 0.0
    return total, matched, pct


def calculate_stats(
    session, tracked_match_id: int, final_set_score: str | None = None
) -> MatchStats:
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

    stats.expected_set_states = _parse_expected_set_states(final_set_score)
    stats.unique_set_states = _count_unique_set_states(session, tracked_match_id)

    stats.odds_at_score_total, stats.odds_at_score_matched, stats.odds_at_score_pct = (
        _odds_at_score_coverage(session, tracked_match_id)
    )

    return stats
