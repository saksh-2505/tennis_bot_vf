"""Confidence-based market matching engine.

Matches TrackedMatch records with BettingSite events using multiple
independent signals, weighted scoring, and persistent attempt logging.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from matcher.signals import (
    signal_competition_type,
    signal_gender,
    signal_player_names,
    signal_scheduled_time,
    signal_tournament,
)

logger = logging.getLogger(__name__)

SIGNAL_WEIGHTS = {
    "player_names": 0.40,
    "tournament": 0.20,
    "scheduled_time": 0.20,
    "gender": 0.10,
    "competition_type": 0.10,
}

HIGH_CONFIDENCE_THRESHOLD = 0.70
MEDIUM_CONFIDENCE_THRESHOLD = 0.40

MAX_CONTINUOUS_RETRY_MINUTES = 180
RETRY_INTERVAL_SECONDS = 120


class MatchConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    REJECTED = "REJECTED"


@dataclass
class CandidateMatch:
    betting_market_id: str
    bt_player_a: str
    bt_player_b: str
    confidence_score: float
    confidence_level: MatchConfidence
    signal_scores: dict[str, float]
    signal_reasons: dict[str, str]
    explanation: str
    rejected: bool = False
    rejection_reason: str = ""


@dataclass
class MarketMatchResult:
    tracked_match_id: int | None = None
    flashscore_match_id: str = ""
    player1_name: str = ""
    player2_name: str = ""
    tournament: str = ""
    candidates: list[CandidateMatch] = field(default_factory=list)
    selected_market_id: str | None = None
    selected_confidence: float = 0.0
    match_found: bool = False
    match_attempted_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


def _compute_confidence(
    fs_name_a: str,
    fs_name_b: str,
    fs_tournament: str,
    fs_time: datetime | None,
    bt_event: dict,
) -> tuple[float, dict[str, float], dict[str, str]]:
    signals: dict[str, Callable] = {
        "player_names": lambda: signal_player_names(
            fs_name_a,
            fs_name_b,
            _bt_name_a(bt_event),
            _bt_name_b(bt_event),
        ),
        "tournament": lambda: signal_tournament(
            fs_tournament, str(bt_event.get("name", "")),
        ),
        "scheduled_time": lambda: signal_scheduled_time(
            fs_time, bt_event,
        ),
        "gender": lambda: signal_gender(
            fs_tournament, bt_event,
        ),
        "competition_type": lambda: signal_competition_type(
            fs_tournament, bt_event,
        ),
    }

    scores: dict[str, float] = {}
    reasons: dict[str, str] = {}
    weighted_total = 0.0
    weight_sum = 0.0

    for name, fn in signals.items():
        try:
            score, reason = fn()
        except Exception:
            logger.debug("Signal %s failed", name, exc_info=True)
            score, reason = 0.0, "error"
        scores[name] = score
        reasons[name] = reason
        w = SIGNAL_WEIGHTS.get(name, 0.1)
        weighted_total += score * w
        weight_sum += w

    if weight_sum > 0:
        weighted_total /= weight_sum

    return weighted_total, scores, reasons


def _bt_name_a(bt_event: dict) -> str:
    name = bt_event.get("name", "")
    if " v " in name:
        return name.split(" v ")[0]
    return bt_event.get("runner_a", name)


def _bt_name_b(bt_event: dict) -> str:
    name = bt_event.get("name", "")
    if " v " in name:
        try:
            return name.split(" v ")[1]
        except IndexError:
            pass
    return bt_event.get("runner_b", "")


def _bt_market_id(bt_event: dict) -> str:
    return str(
        bt_event.get("market_id")
        or bt_event.get("match_odds", {}).get("market_id", "")
    )


def _classify_confidence(score: float) -> MatchConfidence:
    if score >= HIGH_CONFIDENCE_THRESHOLD:
        return MatchConfidence.HIGH
    if score >= MEDIUM_CONFIDENCE_THRESHOLD:
        return MatchConfidence.MEDIUM
    return MatchConfidence.LOW


def match_reason(result: CandidateMatch | None) -> str:
    if result is None:
        return "No betting site events available for matching"
    if result.rejected:
        return f"Rejected: {result.rejection_reason}"
    parts = [f"{k}:{result.signal_reasons.get(k,'?')}[{v:.2f}]"
             for k, v in result.signal_scores.items()]
    return f"[{result.confidence_level.value} cv={result.confidence_score:.3f}] " + ", ".join(parts)


def match_market(
    player1_name: str,
    player2_name: str,
    tournament: str,
    scheduled_start: datetime | None,
    bt_events: list[dict],
    used_market_ids: set[str] | None = None,
) -> MarketMatchResult:
    if used_market_ids is None:
        used_market_ids = set()

    result = MarketMatchResult(
        player1_name=player1_name,
        player2_name=player2_name,
        tournament=tournament,
    )

    if not bt_events:
        result.match_found = False
        return result

    candidates: list[CandidateMatch] = []

    for event in bt_events:
        market_id = _bt_market_id(event)
        if not market_id or market_id in used_market_ids:
            continue

        score, signal_scores, signal_reasons = _compute_confidence(
            player1_name, player2_name, tournament, scheduled_start, event,
        )

        level = _classify_confidence(score)
        rejected = False
        rejection = ""

        if signal_scores.get("player_names", 0) == 0.0:
            rejected = True
            rejection = "no_name_match"
        elif score < 0.15:
            rejected = True
            rejection = f"confidence_too_low:{score:.3f}"

        candidate = CandidateMatch(
            betting_market_id=market_id,
            bt_player_a=_bt_name_a(event),
            bt_player_b=_bt_name_b(event),
            confidence_score=round(score, 4),
            confidence_level=MatchConfidence.REJECTED if rejected else level,
            signal_scores=signal_scores,
            signal_reasons=signal_reasons,
            explanation=match_reason(
                CandidateMatch(
                    betting_market_id=market_id,
                    bt_player_a="",
                    bt_player_b="",
                    confidence_score=score,
                    confidence_level=MatchConfidence.REJECTED if rejected else level,
                    signal_scores=signal_scores,
                    signal_reasons=signal_reasons,
                    explanation="",
                ),
            ) if not rejected else f"REJECTED: {rejection}",
            rejected=rejected,
            rejection_reason=rejection,
        )
        candidates.append(candidate)

    candidates.sort(key=lambda c: c.confidence_score, reverse=True)
    result.candidates = candidates

    best = next((c for c in candidates if not c.rejected), None)
    if best is None:
        result.match_found = False
        _log_all_attempts(result)
        return result

    result.selected_market_id = best.betting_market_id
    result.selected_confidence = best.confidence_score
    result.match_found = True

    if best.confidence_level in (MatchConfidence.HIGH, MatchConfidence.MEDIUM):
        logger.info(
            "Market match: %s vs %s → %s (%s confidence=%.3f)",
            player1_name, player2_name,
            best.betting_market_id,
            best.confidence_level.value,
            best.confidence_score,
        )
    else:
        logger.info(
            "Market match LOW confidence: %s vs %s → %s [%.3f] %s",
            player1_name, player2_name,
            best.betting_market_id,
            best.confidence_score,
            best.explanation,
        )

    _log_all_attempts(result)
    return result


def _log_all_attempts(result: MarketMatchResult) -> None:
    for c in result.candidates:
        if c.rejected:
            logger.debug(
                "REJECTED market %s for %s vs %s: %.3f — %s",
                c.betting_market_id,
                result.player1_name, result.player2_name,
                c.confidence_score, c.rejection_reason,
            )


def _persist_attempt(
    session,
    result: MarketMatchResult,
) -> None:
    from matcher.models import MatchAttempt

    for c in result.candidates:
        attempt = MatchAttempt(
            flashscore_match_id=result.flashscore_match_id or "",
            betting_market_id=c.betting_market_id,
            player1_name=result.player1_name,
            player2_name=result.player2_name,
            tournament=result.tournament,
            confidence_score=c.confidence_score,
            confidence_level=c.confidence_level.value,
            signal_scores=c.signal_scores,
            signal_reasons=c.signal_reasons,
            selected=(c.betting_market_id == result.selected_market_id),
            rejected=c.rejected,
            rejection_reason=c.rejection_reason,
        )
        session.add(attempt)


def match_all(
    tracked_matches: list[Any],
    bt_events: list[dict],
    session=None,
) -> list[MarketMatchResult]:
    results: list[MarketMatchResult] = []
    used_market_ids: set[str] = set()
    if session is not None:
        try:
            from models.tracked_match import TrackedMatch
            assigned = session.query(TrackedMatch.betting_market_id).filter(
                TrackedMatch.betting_market_id.isnot(None)
            ).all()
            used_market_ids.update(row[0] for row in assigned if row[0])
        except Exception:
            pass

    for tm in tracked_matches:
        if tm.betting_market_id:
            continue
        result = match_market(
        result = match_market(
            player1_name=tm.player1_name,
            player2_name=tm.player2_name,
            tournament=tm.tournament,
            scheduled_start=tm.scheduled_start,
            bt_events=bt_events,
            used_market_ids=used_market_ids,
        )
        result.tracked_match_id = tm.id
        result.flashscore_match_id = tm.flashscore_match_id

        if result.match_found and result.selected_market_id:
            if result.selected_market_id not in used_market_ids:
                used_market_ids.add(result.selected_market_id)
                tm.betting_market_id = result.selected_market_id

        results.append(result)

        if session is not None:
            try:
                _persist_attempt(session, result)
            except Exception:
                logger.debug("Failed to persist match attempt", exc_info=True)

    if session is not None:
        try:
            session.commit()
        except Exception:
            logger.debug("Failed to commit match attempts", exc_info=True)

    total_found = sum(1 for r in results if r.match_found)
    logger.info(
        "Matched %d/%d matches to betting markets",
        total_found, len(results),
    )
    return results


def continuous_retry(
    session,
    unmatched_tracked: list[Any],
    bt_events: list[dict],
) -> int:
    assigned = 0

    for tm in unmatched_tracked:
        if tm.betting_market_id:
            continue

        now = datetime.now(timezone.utc)
        if tm.scheduled_start is None:
            continue
        elapsed = (now - tm.scheduled_start).total_seconds()
        if elapsed > MAX_CONTINUOUS_RETRY_MINUTES * 60:
            continue

        result = match_market(
            player1_name=tm.player1_name,
            player2_name=tm.player2_name,
            tournament=tm.tournament,
            scheduled_start=tm.scheduled_start,
            bt_events=bt_events,
        )
        result.tracked_match_id = tm.id
        result.flashscore_match_id = tm.flashscore_match_id

        try:
            _persist_attempt(session, result)
        except Exception:
            pass

        if result.match_found and result.selected_market_id:
            tm.betting_market_id = result.selected_market_id
            assigned += 1
            logger.info(
                "Continuous retry matched: %s vs %s → market %s (%.3f)",
                tm.player1_name, tm.player2_name,
                result.selected_market_id,
                result.selected_confidence,
            )

    if assigned:
        try:
            session.commit()
        except Exception:
            pass

    return assigned
