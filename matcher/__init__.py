"""Confidence-based market matching for Flashscore ↔ Betting Site.

Public API:
    match_market()          — single match candidate scoring
    match_all()             — batch matching with confidence scores
    continuous_retry()      — periodic reassignment for unmatched matches
"""
from matcher.engine import (
    CandidateMatch,
    MatchConfidence,
    MarketMatchResult,
    continuous_retry,
    match_all,
    match_market,
    match_reason,
)
from matcher.signals import (
    extract_signals_from_tracked,
    signal_competition_type,
    signal_gender,
    signal_player_names,
    signal_scheduled_time,
    signal_tournament,
)

__all__ = [
    "CandidateMatch",
    "MarketMatchResult",
    "MatchConfidence",
    "match_market",
    "match_all",
    "continuous_retry",
    "match_reason",
    "extract_signals_from_tracked",
    "signal_player_names",
    "signal_tournament",
    "signal_scheduled_time",
    "signal_gender",
    "signal_competition_type",
]
