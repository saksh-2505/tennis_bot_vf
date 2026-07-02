"""Match validation: score completeness (game states), odds-at-score matching, duration.

Completeness is measured by comparing unique (set_score_a, set_score_b) pairs
against the expected count derived from the final set score. This accounts for
content-hash deduplication: we expect one tick per game-level score transition,
not one per poll interval.
"""
import logging
from dataclasses import dataclass

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


def validate(
    tm: TrackedMatch,
    stats: MatchStats,
    last_set_a: int | None = None,
    last_set_b: int | None = None,
) -> ValidationResult:
    result = ValidationResult()

    # -- Score completeness: actual unique set states >= expected -----------------
    if stats.expected_set_states > 0 and stats.unique_set_states >= stats.expected_set_states:
        result.has_complete_score_data = True
    elif stats.unique_set_states > 0:
        logger.info(
            "Match %d: score completeness %d/%d unique set states",
            tm.id, stats.unique_set_states, stats.expected_set_states,
        )

    # -- Odds-at-score: % of score changes with a nearby odds tick -----------------
    if tm.betting_market_id:
        result.has_complete_odds_data = stats.odds_at_score_pct >= 80.0
        if not result.has_complete_odds_data and stats.odds_at_score_total > 0:
            logger.info(
                "Match %d: odds-at-score coverage %.1f%% (%d/%d)",
                tm.id,
                stats.odds_at_score_pct,
                stats.odds_at_score_matched,
                stats.odds_at_score_total,
            )
    else:
        result.has_complete_odds_data = True

    # -- Readiness flags ----------------------------------------------------------
    result.ready_for_replay = (
        stats.score_tick_count > 0
        and stats.odds_tick_count > 0
    )
    result.ready_for_feature_extraction = stats.score_tick_count >= 10
    result.ready_for_backtesting = (
        result.has_complete_score_data
        and result.has_complete_odds_data
    )

    # -- Overall validation: critical checks --------------------------------------
    critical = True

    if not result.has_complete_score_data:
        logger.warning("Match %d: incomplete score data (%d/%d states)",
                       tm.id, stats.unique_set_states, stats.expected_set_states)
        if stats.expected_set_states > 0 and stats.unique_set_states > 0:
            # Partial data: don't fail, just flag
            pass
        elif stats.unique_set_states == 0:
            critical = False

    duration = tm.match_duration_min or 0
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
