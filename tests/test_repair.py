"""Tests for repair engine, failure classifier, and quality scoring."""
import pytest
from datetime import datetime, timezone

from repair.engine import (
    RepairAction,
    repair_infer_winner,
    repair_recalculate_duration,
    repair_reconstruct_timestamps,
)
from repair.classifier import classify_failure, FailureCategory
from repair.quality import compute_quality, QualityGrade, QualityScores


class FakeTrackedMatch:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeCompletedMatch:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestFailureClassifier:
    def test_none_needed_when_validated(self):
        cm = FakeCompletedMatch(validation_passed=True)
        assert classify_failure(cm, None) == FailureCategory.NONE_NEEDED

    def test_collector_never_started(self):
        cm = FakeCompletedMatch(
            validation_passed=False,
            score_tick_count=0,
            odds_tick_count=0,
            tournament="Wimbledon",
        )
        assert classify_failure(cm, None) == FailureCategory.COLLECTOR_NEVER_STARTED

    def test_score_parsing_failed(self):
        cm = FakeCompletedMatch(
            validation_passed=False,
            score_tick_count=2,
            odds_tick_count=5,
            tournament="Wimbledon",
        )
        assert classify_failure(cm, None) == FailureCategory.SCORE_PARSING_FAILED

    def test_market_assignment_failed(self):
        cm = FakeCompletedMatch(
            validation_passed=False,
            score_tick_count=10,
            odds_tick_count=0,
            tournament="Wimbledon",
        )
        tm = FakeTrackedMatch(betting_market_id=None)
        assert classify_failure(cm, tm) == FailureCategory.MARKET_ASSIGNMENT_FAILED

    def test_odds_parsing_failed_with_market(self):
        cm = FakeCompletedMatch(
            validation_passed=False,
            score_tick_count=10,
            odds_tick_count=0,
            tournament="Wimbledon",
        )
        tm = FakeTrackedMatch(betting_market_id="market_123")
        assert classify_failure(cm, tm) == FailureCategory.ODDS_PARSING_FAILED

    def test_walkover_from_tournament(self):
        cm = FakeCompletedMatch(
            validation_passed=False,
            score_tick_count=0,
            odds_tick_count=0,
            tournament="WALKOVER: Wimbledon",
        )
        assert classify_failure(cm, None) == FailureCategory.WALKOVER


class TestQualityScoring:
    def test_perfect_quality(self):
        cm = FakeCompletedMatch(
            validation_passed=True,
            score_tick_count=100,
            odds_tick_count=300,
            expected_score_states=20,
            unique_score_states=22,
            betting_market_id="m1",
            scheduled_start=datetime.now(timezone.utc),
            actual_finish=datetime.now(timezone.utc),
            duration_minutes=120,
            first_score_timestamp=datetime.now(timezone.utc),
            last_score_timestamp=datetime.now(timezone.utc),
            first_odds_timestamp=datetime.now(timezone.utc),
            last_odds_timestamp=datetime.now(timezone.utc),
            odds_at_score_pct=85.0,
        )
        scores = compute_quality(cm)
        assert scores.overall_grade in (QualityGrade.A, QualityGrade.B)
        assert scores.score_completeness_pct >= 90

    def test_zero_data_quality(self):
        cm = FakeCompletedMatch(
            validation_passed=False,
            score_tick_count=0,
            odds_tick_count=0,
            betting_market_id=None,
            scheduled_start=None,
            actual_finish=None,
            duration_minutes=None,
            first_score_timestamp=None,
            last_score_timestamp=None,
            first_odds_timestamp=None,
            last_odds_timestamp=None,
            odds_at_score_pct=None,
            expected_score_states=0,
            unique_score_states=0,
        )
        scores = compute_quality(cm)
        assert scores.overall_grade == QualityGrade.F
        assert scores.overall_score < 25

    def test_partial_scores_quality(self):
        cm = FakeCompletedMatch(
            validation_passed=False,
            score_tick_count=15,
            odds_tick_count=0,
            betting_market_id=None,
            scheduled_start=datetime.now(timezone.utc),
            actual_finish=datetime.now(timezone.utc),
            duration_minutes=90,
            first_score_timestamp=datetime.now(timezone.utc),
            last_score_timestamp=datetime.now(timezone.utc),
            first_odds_timestamp=None,
            last_odds_timestamp=None,
            odds_at_score_pct=0,
            expected_score_states=20,
            unique_score_states=10,
        )
        scores = compute_quality(cm)
        assert scores.overall_grade in (QualityGrade.C, QualityGrade.D)

    def test_grade_boundaries(self):
        cm = FakeCompletedMatch(
            validation_passed=False,
            score_tick_count=0,
            odds_tick_count=0,
            betting_market_id=None,
            scheduled_start=None,
            actual_finish=None,
            duration_minutes=None,
            first_score_timestamp=None,
            last_score_timestamp=None,
            first_odds_timestamp=None,
            last_odds_timestamp=None,
            odds_at_score_pct=None,
            expected_score_states=0,
            unique_score_states=0,
        )
        scores = compute_quality(cm)
        assert scores.overall_score >= 0
        assert scores.overall_score <= 100
        assert scores.overall_grade in list(QualityGrade)
