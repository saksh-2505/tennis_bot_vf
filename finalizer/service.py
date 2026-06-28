import logging
from datetime import datetime, timezone

from finalizer.stats import calculate_stats
from finalizer.telegram import send_message as send_tg
from finalizer.validation import validate
from models.completed_match import CompletedMatch
from models.live_score import LiveScore
from models.tracked_match import TrackedMatch

logger = logging.getLogger(__name__)

COLLECTOR_VERSION = "3.0.0"


class AlreadyFinalized(Exception):
    pass


class NotFinished(Exception):
    pass


def _get_last_set_scores(
    session, tracked_match_id: int
) -> tuple[int | None, int | None]:
    last_score = (
        session.query(LiveScore)
        .filter(LiveScore.tracked_match_id == tracked_match_id)
        .order_by(LiveScore.timestamp.desc())
        .first()
    )
    if last_score is None:
        return None, None
    return last_score.set_score_a, last_score.set_score_b


def _determine_winner(
    tm: TrackedMatch, last_set_a: int | None, last_set_b: int | None
) -> tuple[int | None, str | None, int | None]:
    if last_set_a is None or last_set_b is None:
        return None, None, None

    if last_set_a > last_set_b:
        winner = tm.player1_id
    elif last_set_b > last_set_a:
        winner = tm.player2_id
    else:
        return None, None, None

    final_set_score = f"{last_set_a}-{last_set_b}"
    total_sets = last_set_a + last_set_b
    return winner, final_set_score, total_sets


def finalize_match(session, tracked_match_id: int) -> CompletedMatch:
    tm = session.get(TrackedMatch, tracked_match_id)
    if tm is None:
        raise ValueError(f"TrackedMatch {tracked_match_id} not found")
    if tm.status != "FINISHED":
        raise NotFinished(
            f"TrackedMatch {tracked_match_id} has status {tm.status!r}, "
            f"expected FINISHED"
        )

    existing = (
        session.query(CompletedMatch)
        .filter(CompletedMatch.tracked_match_id == tracked_match_id)
        .first()
    )
    if existing is not None:
        raise AlreadyFinalized(
            f"TrackedMatch {tracked_match_id} already finalized "
            f"(CompletedMatch id={existing.id})"
        )

    stats = calculate_stats(session, tracked_match_id)
    last_set_a, last_set_b = _get_last_set_scores(session, tracked_match_id)
    validation = validate(tm, stats, last_set_a=last_set_a, last_set_b=last_set_b)
    winner, final_set_score, total_sets = _determine_winner(
        tm, last_set_a, last_set_b
    )

    now = datetime.now(timezone.utc)
    cm = CompletedMatch(
        tracked_match_id=tm.id,
        flashscore_match_id=tm.flashscore_match_id,
        betting_market_id=tm.betting_market_id,
        player1_id=tm.player1_id,
        player2_id=tm.player2_id,
        tournament=tm.tournament,
        round=tm.round,
        surface=tm.surface,
        scheduled_start=tm.scheduled_start,
        actual_finish=tm.actual_finish,
        duration_minutes=tm.match_duration_min,
        winner_player_id=winner,
        final_set_score=final_set_score,
        total_sets=total_sets,
        score_tick_count=stats.score_tick_count,
        odds_tick_count=stats.odds_tick_count,
        first_score_timestamp=stats.first_score_timestamp,
        last_score_timestamp=stats.last_score_timestamp,
        first_odds_timestamp=stats.first_odds_timestamp,
        last_odds_timestamp=stats.last_odds_timestamp,
        score_collection_duration_seconds=stats.score_collection_duration_seconds,
        odds_collection_duration_seconds=stats.odds_collection_duration_seconds,
        duplicate_score_ticks=stats.duplicate_score_ticks,
        duplicate_odds_ticks=stats.duplicate_odds_ticks,
        largest_score_gap_seconds=stats.largest_score_gap_seconds,
        largest_odds_gap_seconds=stats.largest_odds_gap_seconds,
        has_complete_score_data=validation.has_complete_score_data,
        has_complete_odds_data=validation.has_complete_odds_data,
        ready_for_replay=validation.ready_for_replay,
        ready_for_feature_extraction=validation.ready_for_feature_extraction,
        ready_for_backtesting=validation.ready_for_backtesting,
        validation_passed=validation.validation_passed,
        exported=False,
        finalized_at=now,
        collector_version=COLLECTOR_VERSION,
    )
    session.add(cm)
    session.commit()
    session.refresh(cm)

    label = f"{tm.player1_name} vs {tm.player2_name}"
    logger.info(
        "Match %d (%s) finalized — "
        "Score ticks: %s  Odds ticks: %s  Duration: %s min  "
        "Validation: %s",
        tracked_match_id,
        label,
        f"{stats.score_tick_count:,}",
        f"{stats.odds_tick_count:,}",
        tm.match_duration_min or "?",
        "PASS" if validation.validation_passed else "FAIL",
    )

    try:
        pass_str = "\u2705 PASS" if validation.validation_passed else "\u274c FAIL"
        tg_msg = (
            f"\U0001f3bd Match Finalized: {tracked_match_id}\n"
            f"{tm.player1_name} vs {tm.player2_name}\n"
            f"Duration: {tm.match_duration_min or '?'} min\n"
            f"Score ticks: {stats.score_tick_count:,}\n"
            f"Odds ticks: {stats.odds_tick_count:,}\n"
            f"Validation: {pass_str}"
        )
        send_tg(tg_msg)
    except Exception:
        logger.debug("Telegram notification failed for match %d", tracked_match_id)

    return cm


def run_match_finalizer(session) -> list[CompletedMatch]:
    not_finalized = (
        session.query(TrackedMatch)
        .filter(
            TrackedMatch.status == "FINISHED",
            ~TrackedMatch.id.in_(
                session.query(CompletedMatch.tracked_match_id)
                .select_from(CompletedMatch)
            ),
        )
        .all()
    )

    if not not_finalized:
        logger.info("No matches to finalize")
        return []

    created: list[CompletedMatch] = []
    for tm in not_finalized:
        try:
            cm = finalize_match(session, tm.id)
            created.append(cm)
        except AlreadyFinalized:
            logger.info("Match %d already finalized — skipping", tm.id)
        except Exception:
            logger.exception(
                "Match %d finalization failed", tm.id
            )

    logger.info(
        "Finalized %d / %d matches",
        len(created),
        len(not_finalized),
    )
    return created
