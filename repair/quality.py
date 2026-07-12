"""Quality scoring — A/B/C/D/F grade for every completed match."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.completed_match import CompletedMatch

import logging

logger = logging.getLogger(__name__)


class QualityGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


@dataclass
class QualityScores:
    score_completeness_pct: float
    odds_completeness_pct: float
    timeline_completeness_pct: float
    synchronization_score: float
    validation_score: float
    overall_grade: QualityGrade
    overall_score: float


def compute_quality(cm: "CompletedMatch") -> QualityScores:
    score_pct = _score_completeness(cm)
    odds_pct = _odds_completeness(cm)
    timeline_pct = _timeline_completeness(cm)
    sync_score = _synchronization_score(cm)
    validation_score = 100.0 if cm.validation_passed else (
        50.0 if cm.score_tick_count > 0 else 0.0
    )

    weights = {
        "score": 0.25,
        "odds": 0.25,
        "timeline": 0.15,
        "sync": 0.20,
        "validation": 0.15,
    }

    overall = (
        score_pct * weights["score"]
        + odds_pct * weights["odds"]
        + timeline_pct * weights["timeline"]
        + sync_score * weights["sync"]
        + validation_score * weights["validation"]
    )

    if overall >= 90:
        grade = QualityGrade.A
    elif overall >= 75:
        grade = QualityGrade.B
    elif overall >= 50:
        grade = QualityGrade.C
    elif overall >= 25:
        grade = QualityGrade.D
    else:
        grade = QualityGrade.F

    return QualityScores(
        score_completeness_pct=round(score_pct, 1),
        odds_completeness_pct=round(odds_pct, 1),
        timeline_completeness_pct=round(timeline_pct, 1),
        synchronization_score=round(sync_score, 1),
        validation_score=round(validation_score, 1),
        overall_grade=grade,
        overall_score=round(overall, 1),
    )


def _score_completeness(cm) -> float:
    if cm.score_tick_count == 0:
        return 0.0

    if cm.expected_score_states and cm.expected_score_states > 0:
        ratio = cm.unique_score_states / cm.expected_score_states
        return min(100.0, ratio * 100.0)

    if cm.score_tick_count >= 50:
        return 90.0
    if cm.score_tick_count >= 20:
        return 70.0
    if cm.score_tick_count >= 10:
        return 50.0
    if cm.score_tick_count >= 3:
        return 25.0
    return 10.0


def _odds_completeness(cm) -> float:
    if cm.betting_market_id is None:
        return 0.0

    if cm.odds_tick_count == 0:
        return 0.0

    if cm.odds_tick_count >= 200:
        return 95.0
    if cm.odds_tick_count >= 100:
        return 80.0
    if cm.odds_tick_count >= 50:
        return 60.0
    if cm.odds_tick_count >= 10:
        return 40.0
    return 20.0


def _timeline_completeness(cm) -> float:
    score = 100.0

    if cm.scheduled_start is None:
        score -= 20
    if cm.actual_finish is None:
        score -= 20
    if cm.duration_minutes is None or cm.duration_minutes <= 0:
        score -= 20
    if cm.first_score_timestamp is None:
        score -= 20
    if cm.last_score_timestamp is None:
        score -= 10
    if cm.first_odds_timestamp is None and cm.betting_market_id:
        score -= 10

    return max(0.0, score)


def _synchronization_score(cm) -> float:
    if cm.odds_at_score_pct and cm.odds_at_score_pct > 0:
        return cm.odds_at_score_pct

    if cm.score_tick_count > 0 and cm.odds_tick_count > 0:
        return 30.0
    if cm.score_tick_count > 0 and cm.betting_market_id is None:
        return 100.0
    if cm.odds_tick_count > 0:
        return 50.0
    return 0.0


def apply_quality_to_db(session, cm, scores: QualityScores) -> None:
    cm.score_completeness_pct = scores.score_completeness_pct
    cm.odds_completeness_pct = scores.odds_completeness_pct
    cm.timeline_completeness_pct = scores.timeline_completeness_pct
    cm.synchronization_score = scores.synchronization_score
    cm.quality_grade = scores.overall_grade.value
    cm.quality_score = scores.overall_score


def score_all(session, cm_list) -> dict[str, int]:
    grades: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}

    for cm in cm_list:
        scores = compute_quality(cm)
        apply_quality_to_db(session, cm, scores)
        grades[scores.overall_grade.value] += 1

    session.commit()
    return grades
