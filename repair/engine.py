"""Data repair engine — repairs recoverable data on completed matches.

Never overwrites raw collected data (live_scores, live_odds).
Only updates derived fields on completed_matches and tracked_matches.
Every repair is logged.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.completed_match import CompletedMatch
    from models.tracked_match import TrackedMatch

logger = logging.getLogger(__name__)


class RepairAction(str, Enum):
    INFER_WINNER = "infer_winner"
    RECALCULATE_DURATION = "recalculate_duration"
    RECONSTRUCT_TIMESTAMPS = "reconstruct_timestamps"
    RETRY_MARKET_ASSIGNMENT = "retry_market_assignment"
    RESOLVE_PLAYER_REFERENCES = "resolve_player_references"
    RECOMPUTE_VALIDATION = "recompute_validation"
    RECALCULATE_STATS = "recalculate_stats"


def repair_infer_winner(session, cm, tm) -> tuple[bool, str]:
    if cm.winner_player_id is not None:
        return False, "already_set"

    from models.live_score import LiveScore

    last = (
        session.query(LiveScore)
        .filter(LiveScore.tracked_match_id == cm.tracked_match_id)
        .order_by(LiveScore.timestamp.desc())
        .first()
    )
    if last is None:
        return False, "no_score_data"

    if last.set_score_a is None or last.set_score_b is None:
        return False, "no_set_scores"

    if last.set_score_a > last.set_score_b:
        winner = tm.player1_id or cm.player1_id
    elif last.set_score_b > last.set_score_a:
        winner = tm.player2_id or cm.player2_id
    else:
        return False, "sets_tied"

    cm.winner_player_id = winner
    cm.final_set_score = f"{last.set_score_a}-{last.set_score_b}"
    cm.total_sets = last.set_score_a + last.set_score_b
    return True, f"winner={winner} sets={cm.final_set_score}"


def repair_recalculate_duration(session, cm, tm) -> tuple[bool, str]:
    from models.live_score import LiveScore
    from sqlalchemy import func

    actual_finish = cm.actual_finish or tm.actual_finish
    if actual_finish is None:
        return False, "no_finish_time"

    first_score = (
        session.query(func.min(LiveScore.timestamp))
        .filter(LiveScore.tracked_match_id == cm.tracked_match_id)
        .scalar()
    )

    start = first_score or cm.scheduled_start
    if start is None:
        return False, "no_start_time"

    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if actual_finish.tzinfo is None:
        actual_finish = actual_finish.replace(tzinfo=timezone.utc)

    delta = (actual_finish - start).total_seconds()
    if delta <= 0:
        return False, "negative_duration"
    if delta > 86400:
        return False, "duration_too_long"

    new_duration = int(delta / 60)
    old = cm.duration_minutes
    cm.duration_minutes = new_duration
    if tm.match_duration_min is None or tm.match_duration_min != new_duration:
        tm.match_duration_min = new_duration

    if old != new_duration:
        return True, f"duration:{old}→{new_duration}min"
    return False, "unchanged"


def repair_reconstruct_timestamps(session, cm, tm) -> tuple[bool, str]:
    from models.live_score import LiveScore
    from models.live_odds import LiveOdds
    from sqlalchemy import func

    fixed = []

    if cm.first_score_timestamp is None or cm.last_score_timestamp is None:
        result = (
            session.query(
                func.min(LiveScore.timestamp),
                func.max(LiveScore.timestamp),
            )
            .filter(LiveScore.tracked_match_id == cm.tracked_match_id)
            .first()
        )
        if result and result[0]:
            cm.first_score_timestamp = result[0]
            cm.last_score_timestamp = result[1]
            if result[0] and result[1]:
                delta = (result[1] - result[0]).total_seconds()
                cm.score_collection_duration_seconds = int(delta)
            fixed.append("score_ts")

    if cm.first_odds_timestamp is None or cm.last_odds_timestamp is None:
        result = (
            session.query(
                func.min(LiveOdds.timestamp),
                func.max(LiveOdds.timestamp),
            )
            .filter(LiveOdds.tracked_match_id == cm.tracked_match_id)
            .first()
        )
        if result and result[0]:
            cm.first_odds_timestamp = result[0]
            cm.last_odds_timestamp = result[1]
            if result[0] and result[1]:
                delta = (result[1] - result[0]).total_seconds()
                cm.odds_collection_duration_seconds = int(delta)
            fixed.append("odds_ts")

    if fixed:
        return True, f"reconstructed:{','.join(fixed)}"
    return False, "all_present"


def repair_retry_market_assignment(
    session, cm, tm,
) -> tuple[bool, str]:
    if tm.betting_market_id is not None:
        if cm.betting_market_id is None:
            cm.betting_market_id = tm.betting_market_id
            return True, "market_copied_from_tm"
        return False, "already_assigned"

    from models.bettingsite import BettingsiteFoundMatch
    from matcher.signals import signal_player_names

    bt_events = session.query(BettingsiteFoundMatch).all()
    if not bt_events:
        return False, "no_bt_events"

    best_score = 0.0
    best_market_id: str | None = None

    for bt in bt_events:
        score, _ = signal_player_names(
            tm.player1_name, tm.player2_name,
            bt.player_a, bt.player_b,
        )
        if score > best_score and score >= 0.6:
            best_score = score
            best_market_id = bt.market_id

    if best_market_id is None:
        return False, f"no_match_above_threshold_best={best_score:.2f}"

    tm.betting_market_id = best_market_id
    cm.betting_market_id = best_market_id
    return True, f"retroactively_assigned_market={best_market_id}_score={best_score:.2f}"


def repair_resolve_player_references(
    session, cm, tm,
) -> tuple[bool, str]:
    fixed = []

    if cm.player1_id is None and tm.player1_id is not None:
        cm.player1_id = tm.player1_id
        fixed.append("p1")

    if cm.player2_id is None and tm.player2_id is not None:
        cm.player2_id = tm.player2_id
        fixed.append("p2")

    if fixed:
        return True, f"resolved:{','.join(fixed)}"
    return False, "all_present"


def repair_recompute_validation(
    session, cm, tm,
) -> tuple[bool, str]:
    from finalizer.stats import calculate_stats
    from finalizer.validation import validate

    stats = calculate_stats(
        session, cm.tracked_match_id, final_set_score=cm.final_set_score,
    )
    last_set_a, last_set_b = None, None
    if cm.final_set_score:
        parts = cm.final_set_score.split("-")
        if len(parts) == 2:
            try:
                last_set_a = int(parts[0])
                last_set_b = int(parts[1])
            except ValueError:
                pass

    validation = validate(tm, stats, last_set_a=last_set_a, last_set_b=last_set_b)

    changes = []
    for attr in (
        "has_complete_score_data",
        "has_complete_odds_data",
        "ready_for_replay",
        "ready_for_feature_extraction",
        "ready_for_backtesting",
        "validation_passed",
    ):
        old = getattr(cm, attr)
        new = getattr(validation, attr)
        if old != new:
            setattr(cm, attr, new)
            changes.append(f"{attr}:{old}→{new}")

    if changes:
        return True, f"recomputed:{','.join(changes)}"
    return False, "unchanged"


def repair_recalculate_stats(session, cm, tm) -> tuple[bool, str]:
    from finalizer.stats import calculate_stats

    stats = calculate_stats(
        session, cm.tracked_match_id, final_set_score=cm.final_set_score,
    )

    changes = []
    stat_fields = [
        ("score_tick_count", stats.score_tick_count),
        ("odds_tick_count", stats.odds_tick_count),
        ("duplicate_score_ticks", stats.duplicate_score_ticks),
        ("duplicate_odds_ticks", stats.duplicate_odds_ticks),
        ("largest_score_gap_seconds", stats.largest_score_gap_seconds),
        ("largest_odds_gap_seconds", stats.largest_odds_gap_seconds),
        ("expected_score_states", stats.expected_set_states),
        ("unique_score_states", stats.unique_set_states),
        ("odds_at_score_pct", stats.odds_at_score_pct),
    ]

    for attr, new_val in stat_fields:
        old = getattr(cm, attr, None)
        if old != new_val and new_val is not None:
            setattr(cm, attr, new_val)
            changes.append(f"{attr}:{old}→{new_val}")

    if changes:
        return True, f"recalculated:{len(changes)}_fields"
    return False, "unchanged"


REPAIR_HANDLERS = {
    RepairAction.INFER_WINNER: repair_infer_winner,
    RepairAction.RECALCULATE_DURATION: repair_recalculate_duration,
    RepairAction.RECONSTRUCT_TIMESTAMPS: repair_reconstruct_timestamps,
    RepairAction.RETRY_MARKET_ASSIGNMENT: repair_retry_market_assignment,
    RepairAction.RESOLVE_PLAYER_REFERENCES: repair_resolve_player_references,
    RepairAction.RECOMPUTE_VALIDATION: repair_recompute_validation,
    RepairAction.RECALCULATE_STATS: repair_recalculate_stats,
}


def run_repairs(
    session,
    cm,
    tm,
    actions: list[RepairAction] | None = None,
) -> dict[str, dict]:
    if actions is None:
        actions = list(RepairAction)

    results: dict[str, dict] = {}

    for action in actions:
        handler = REPAIR_HANDLERS.get(action)
        if handler is None:
            results[action.value] = {"repaired": False, "reason": "unknown_handler"}
            continue

        try:
            repaired, reason = handler(session, cm, tm)
            results[action.value] = {
                "repaired": repaired,
                "reason": reason,
            }
            if repaired:
                logger.info(
                    "Repair %s: match %d — %s",
                    action.value, cm.tracked_match_id, reason,
                )
        except Exception:
            logger.exception(
                "Repair %s failed for match %d",
                action.value, cm.tracked_match_id,
            )
            results[action.value] = {"repaired": False, "reason": "exception"}

    return results


def run_repairs_on_all(session, cm_list, tm_map) -> dict[str, int]:
    stats = {
        "total": len(cm_list),
        "repaired": 0,
        "unchanged": 0,
        "individual_fixes": 0,
    }

    for cm in cm_list:
        tm = tm_map.get(cm.tracked_match_id)
        if tm is None:
            continue

        results = run_repairs(session, cm, tm)
        any_repaired = any(r["repaired"] for r in results.values())
        if any_repaired:
            stats["repaired"] += 1
            stats["individual_fixes"] += sum(
                1 for r in results.values() if r["repaired"]
            )
        else:
            stats["unchanged"] += 1

    session.commit()
    return stats
