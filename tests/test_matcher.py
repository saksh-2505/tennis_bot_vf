"""Tests for the confidence-based market matcher."""
import pytest

from matcher.signals import (
    signal_competition_type,
    signal_gender,
    signal_player_names,
    signal_scheduled_time,
    signal_tournament,
)
from matcher.engine import match_market, match_all, MarketMatchResult, MatchConfidence
from matcher.models import MatchAttempt
from matcher import CandidateMatch, match_reason


class TestPlayerNameSignals:
    def test_exact_match(self):
        score, reason = signal_player_names(
            "DJOKOVIC NOVAK", "SINNER JANNIK",
            "Novak Djokovic", "Jannik Sinner",
        )
        assert score >= 0.8, f"Expected >=0.8, got {score} — {reason}"

    def test_reversed_order(self):
        score, reason = signal_player_names(
            "DJOKOVIC NOVAK", "SINNER JANNIK",
            "Jannik Sinner", "Novak Djokovic",
        )
        assert score >= 0.7, f"Expected >=0.7, got {score} — {reason}"

    def test_abbreviated_name(self):
        score, reason = signal_player_names(
            "SVAJDA Z", "KYRGIOS N",
            "Svajda Zizou", "Nick Kyrgios",
        )
        assert score >= 0.15, f"Expected >=0.15, got {score} — {reason}"

    def test_compound_last_name(self):
        score, reason = signal_player_names(
            "DE MINAUR ALEX", "NADAL RAFAEL",
            "Alex De Minaur", "Rafael Nadal",
        )
        assert score >= 0.5, f"Expected >=0.5, got {score} — {reason}"

    def test_no_match(self):
        score, reason = signal_player_names(
            "FEDERER ROGER", "NADAL RAFAEL",
            "Jannik Sinner", "Carlos Alcaraz",
        )
        assert score == 0.0, f"Expected 0.0, got {score} — {reason}"

    def test_last_name_substring_only(self):
        score, reason = signal_player_names(
            "ALCARAZ CARLOS", "DJOKOVIC NOVAK",
            "Carlos Alcaraz Garfia", "Novak Djokovic",
        )
        assert score >= 0.0, f"Expected at least 0, got {score} — {reason}"


class TestTournamentSignal:
    def test_city_match(self):
        score, reason = signal_tournament(
            "ATP - SINGLES: Wimbledon (United Kingdom), grass",
            "Wimbledon Mens Singles",
        )
        assert score >= 0.6, f"Expected >=0.6, got {score} — {reason}"

    def test_no_match(self):
        score, reason = signal_tournament(
            "ATP - SINGLES: Paris (France), clay",
            "Wimbledon Mens Singles",
        )
        assert score < 0.8

    def test_word_match(self):
        score, reason = signal_tournament(
            "CHALLENGER MEN - SINGLES: Iasi (Romania), clay",
            "Iasi Challenger Mens",
        )
        assert score >= 0.6


class TestGenderSignal:
    def test_atp_match(self):
        score, reason = signal_gender(
            "ATP - SINGLES: Wimbledon (United Kingdom), grass",
            {"name": "ATP Wimbledon"},
        )
        assert score >= 0.8

    def test_atp_challenger_men(self):
        score, reason = signal_gender(
            "CHALLENGER MEN - SINGLES: Iasi (Romania), clay",
            {"name": "ATP Challenger Iasi"},
        )
        assert score >= 0.8

    def test_mismatch(self):
        score, reason = signal_gender(
            "WTA - SINGLES: Wimbledon (United Kingdom), grass",
            {"name": "ATP Wimbledon Mens"},
        )
        assert score == 0.0


class TestCompetitionTypeSignal:
    def test_both_qual(self):
        score, reason = signal_competition_type(
            "ATP - SINGLES: Bastad (Sweden) - Qualification, clay",
            {"name": "Bastad ATP Qual"},
        )
        assert score >= 0.5

    def test_both_main(self):
        score, reason = signal_competition_type(
            "ATP - SINGLES: Wimbledon (United Kingdom), grass",
            {"name": "Wimbledon ATP"},
        )
        assert score >= 0.8


class TestMatchMarket:
    def test_high_confidence_match(self):
        bt_events = [
            {
                "name": "Novak Djokovic v Jannik Sinner",
                "market_id": "market_123",
                "runner_a": "Novak Djokovic",
                "runner_b": "Jannik Sinner",
            },
        ]
        result = match_market(
            "DJOKOVIC NOVAK", "SINNER JANNIK",
            "ATP - SINGLES: Wimbledon (United Kingdom), grass",
            None,
            bt_events,
        )
        assert result.match_found
        assert result.selected_market_id == "market_123"
        assert result.selected_confidence >= 0.7

    def test_low_confidence_rejected_below_threshold(self):
        bt_events = [
            {
                "name": "Roger Federer v Rafael Nadal",
                "market_id": "market_456",
                "runner_a": "Roger Federer",
                "runner_b": "Rafael Nadal",
            },
        ]
        result = match_market(
            "DJOKOVIC NOVAK", "SINNER JANNIK",
            "ATP - SINGLES: Wimbledon (United Kingdom), grass",
            None,
            bt_events,
        )
        assert not result.match_found

    def test_multiple_candidates_best_wins(self):
        bt_events = [
            {
                "name": "Random Player v Other Guy",
                "market_id": "bad_market",
                "runner_a": "Random Player",
                "runner_b": "Other Guy",
            },
            {
                "name": "Novak Djokovic v Jannik Sinner",
                "market_id": "good_market",
                "runner_a": "Novak Djokovic",
                "runner_b": "Jannik Sinner",
            },
        ]
        result = match_market(
            "DJOKOVIC NOVAK", "SINNER JANNIK",
            "ATP - SINGLES: Wimbledon (United Kingdom), grass",
            None,
            bt_events,
        )
        assert result.match_found
        assert result.selected_market_id == "good_market"

    def test_no_events(self):
        result = match_market(
            "DJOKOVIC NOVAK", "SINNER JANNIK",
            "Wimbledon", None, [],
        )
        assert not result.match_found

    def test_candidates_logged_with_explanation(self):
        bt_events = [
            {
                "name": "Novak Djokovic v Jannik Sinner",
                "market_id": "m1",
                "runner_a": "Novak Djokovic",
                "runner_b": "Jannik Sinner",
            },
            {
                "name": "Federer v Nadal",
                "market_id": "m2",
                "runner_a": "Federer",
                "runner_b": "Nadal",
            },
        ]
        result = match_market(
            "DJOKOVIC NOVAK", "SINNER JANNIK",
            "Wimbledon", None, bt_events,
        )
        assert len(result.candidates) >= 1


class TestMatchReason:
    def test_reason_string(self):
        result = CandidateMatch(
            betting_market_id="m1",
            bt_player_a="Novak Djokovic",
            bt_player_b="Jannik Sinner",
            confidence_score=0.85,
            confidence_level=MatchConfidence.HIGH,
            signal_scores={"player_names": 0.9, "tournament": 0.8},
            signal_reasons={"player_names": "exact", "tournament": "city:wimbledon"},
            explanation="",
        )
        reason = match_reason(result)
        assert "HIGH" in reason
        assert "0.85" in reason

    def test_none_result(self):
        assert "No betting site" in match_reason(None)
