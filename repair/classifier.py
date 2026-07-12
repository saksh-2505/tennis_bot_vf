"""Failure classification — every incomplete match gets exactly one primary category."""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.completed_match import CompletedMatch
    from models.tracked_match import TrackedMatch

import logging

logger = logging.getLogger(__name__)


class FailureCategory(str, Enum):
    MARKET_ASSIGNMENT_FAILED = "market_assignment_failed"
    COLLECTOR_NEVER_STARTED = "collector_never_started"
    COLLECTOR_STARTED_LATE = "collector_started_late"
    SCORE_PARSING_FAILED = "score_parsing_failed"
    ODDS_PARSING_FAILED = "odds_parsing_failed"
    DATABASE_WRITE_FAILED = "database_write_failed"
    FLASHSCORE_UNAVAILABLE = "flashscore_unavailable"
    BETTING_SITE_UNAVAILABLE = "betting_site_unavailable"
    MATCH_CANCELLED = "match_cancelled"
    WALKOVER = "walkover"
    RETIREMENT = "retirement"
    NONE_NEEDED = "none_needed"
    UNKNOWN = "unknown"


CATEGORY_PRIORITY = [
    FailureCategory.MATCH_CANCELLED,
    FailureCategory.WALKOVER,
    FailureCategory.RETIREMENT,
    FailureCategory.MARKET_ASSIGNMENT_FAILED,
    FailureCategory.COLLECTOR_NEVER_STARTED,
    FailureCategory.COLLECTOR_STARTED_LATE,
    FailureCategory.SCORE_PARSING_FAILED,
    FailureCategory.ODDS_PARSING_FAILED,
    FailureCategory.DATABASE_WRITE_FAILED,
    FailureCategory.FLASHSCORE_UNAVAILABLE,
    FailureCategory.BETTING_SITE_UNAVAILABLE,
]


def classify_failure(cm: "CompletedMatch", tm: "TrackedMatch" | None) -> FailureCategory:
    if cm.validation_passed:
        return FailureCategory.NONE_NEEDED

    tournament_upper = (cm.tournament or "").upper()
    if "WALKOVER" in tournament_upper:
        return FailureCategory.WALKOVER
    if "RETIRED" in tournament_upper or "RETIREMENT" in tournament_upper:
        return FailureCategory.RETIREMENT
    if "CANCEL" in tournament_upper:
        return FailureCategory.MATCH_CANCELLED

    if cm.score_tick_count == 0 and cm.odds_tick_count == 0:
        return FailureCategory.COLLECTOR_NEVER_STARTED

    if cm.score_tick_count > 0 and cm.score_tick_count < 3:
        return FailureCategory.SCORE_PARSING_FAILED

    if cm.score_tick_count > 0 and cm.odds_tick_count == 0:
        if tm is not None and tm.betting_market_id:
            return FailureCategory.ODDS_PARSING_FAILED
        return FailureCategory.MARKET_ASSIGNMENT_FAILED

    if cm.score_tick_count > 0 and cm.odds_tick_count > 0:
        if not cm.has_complete_score_data:
            return FailureCategory.COLLECTOR_STARTED_LATE
        if not cm.has_complete_odds_data:
            return FailureCategory.COLLECTOR_STARTED_LATE

    return FailureCategory.UNKNOWN


def classify_all(completed_matches, tm_map) -> dict[str, int]:
    counts: dict[str, int] = {}

    for cm in completed_matches:
        tm = tm_map.get(cm.tracked_match_id)
        category = classify_failure(cm, tm)
        counts[category.value] = counts.get(category.value, 0) + 1

    return counts
