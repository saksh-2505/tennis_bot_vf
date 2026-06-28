import logging
from dataclasses import dataclass

from config import settings
from finalizer.stats import MatchStats
from models.tracked_match import TrackedMatch

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    validation_passed: bool = False
    has_complete_score_data: bool = False
    has_complete_odds_data: bool = False
    ready_for_replay: bool = False
    ready_for_feature_extraction: bool = False
    ready_for_backtesting: bool = False


def _has_80pct(actual: int, duration_seconds: int | None, interval: int) -> bool:
    if duration_seconds is None or duration_seconds <= 0:
        return actual > 0
    expected = duration_seconds / interval
    return actual >= 0.8 * expected


def validate(
    tm: TrackedMatch,
    stats: MatchStats,
    last_set_a: int | None = None,
    last_set_b: int | None = None,
) -> ValidationResult:
    result = ValidationResult()

    duration = tm.match_duration_min or 0

    # completeness at 80% threshold
    result.has_complete_score_data = _has_80pct(
        stats.score_tick_count,
        stats.score_collection_duration_seconds,
        settings.LIVE_SCORE_INTERVAL_SECONDS,
    )
    result.has_complete_odds_data = _has_80pct(
        stats.odds_tick_count,
        stats.odds_collection_duration_seconds,
        settings.LIVE_ODDS_INTERVAL_SECONDS,
    )

    # derived readiness
    result.ready_for_replay = (
        stats.score_tick_count > 0
        and stats.odds_tick_count > 0
        and stats.largest_score_gap_seconds is not None
        and stats.largest_score_gap_seconds < 60
        and stats.largest_odds_gap_seconds is not None
        and stats.largest_odds_gap_seconds < 30
    )
    result.ready_for_feature_extraction = stats.score_tick_count >= 10
    result.ready_for_backtesting = (
        result.has_complete_score_data and result.has_complete_odds_data
    )

    # overall validation — all critical checks must pass
    critical = True

    if stats.score_tick_count == 0:
        logger.warning("Match %d: no score ticks", tm.id)
        critical = False
    if stats.odds_tick_count == 0:
        logger.warning("Match %d: no odds ticks", tm.id)
    if duration <= 0:
        logger.warning("Match %d: invalid duration %d", tm.id, duration)
        critical = False
    if last_set_a is None or last_set_b is None:
        logger.warning("Match %d: no final set score available", tm.id)
        critical = False
    elif last_set_a == last_set_b:
        logger.warning("Match %d: sets tied %d-%d, no winner", tm.id, last_set_a, last_set_b)
        critical = False

    result.validation_passed = critical

    return result
