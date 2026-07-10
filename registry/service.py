"""Match registry. Cross-references Flashscore matches with Betting Site markets."""
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import or_
from sqlalchemy.orm import Session

from collector.betting_site.parser import _extract_last_name, _names_match
from database import engine

if TYPE_CHECKING:
    from models.tracked_match import TrackedMatch

logger = logging.getLogger(__name__)


def _find_player(session, name: str):
    """Look up a player by name, trying multiple formats.

    Flashscore names are "FIRST LAST" (e.g. "SVAJDA Z"), while the
    players table stores "LAST FIRST" (e.g. "SVAJDA ZIZOU").  Try
    exact match, reversed order, last-name partial, and handle
    abbreviated names where first name is just an initial.
    """
    from models.player import Player

    p = session.query(Player).filter_by(full_name=name).first()
    if p:
        return p

    parts = name.split()
    if len(parts) >= 2:
        last_first = " ".join(reversed(parts))
        p = session.query(Player).filter_by(full_name=last_first).first()
        if p:
            return p

        # Determine last name — if the final word is short (initials),
        # use all preceding words as the last name
        if len(parts[-1]) <= 2:
            last_name = " ".join(parts[:-1])
        else:
            last_name = parts[-1]

        if len(last_name) >= 3:
            p = session.query(Player).filter(
                or_(
                    Player.full_name.ilike(f"{last_name} %"),
                    Player.full_name.ilike(f"% {last_name}"),
                    Player.full_name.ilike(f"%{last_name}%"),
                )
            ).first()
            if p:
                return p

    return None


def build_match_registry() -> list["TrackedMatch"]:
    import database as db

    from models.bettingsite import BettingsiteFoundMatch
    from models.flashscore import FlashscoreFoundMatch
    from models.tracked_match import TrackedMatch

    TrackedMatch.metadata.create_all(bind=engine)

    results: list[TrackedMatch] = []

    with db.SessionLocal() as session:
        fs_matches = session.query(FlashscoreFoundMatch).all()
        bt_matches = session.query(BettingsiteFoundMatch).all()

        used_bt_market_ids: set[str] = set()

        for fs in fs_matches:
            fs_last_a = _extract_last_name(fs.player_a)
            fs_last_b = _extract_last_name(fs.player_b)

            candidates: list[BettingsiteFoundMatch] = []
            for bt in bt_matches:
                if bt.market_id in used_bt_market_ids:
                    continue
                event_name = f"{bt.player_a} v {bt.player_b}".lower()
                if _names_match(event_name, fs_last_a, fs_last_b) or _names_match(event_name, fs_last_b, fs_last_a):
                    candidates.append(bt)

            p1 = _find_player(session, fs.player_a)
            p2 = _find_player(session, fs.player_b)

            betting_market_id: str | None = None

            if not candidates:
                logger.info(
                    "Flashscore match %s (%s vs %s) has no betting market — scores only",
                    fs.flashscore_match_id, fs.player_a, fs.player_b,
                )
            else:
                if len(candidates) > 1:
                    logger.warning(
                        "Flashscore match %s (%s vs %s) has %d matching betting markets — using first",
                        fs.flashscore_match_id, fs.player_a, fs.player_b, len(candidates),
                    )
                bt = candidates[0]
                betting_market_id = bt.market_id
                used_bt_market_ids.add(bt.market_id)

            if not p1:
                logger.warning(
                    "Player %s not found in players table for Flashscore match %s",
                    fs.player_a, fs.flashscore_match_id,
                )
            if not p2:
                logger.warning(
                    "Player %s not found in players table for Flashscore match %s",
                    fs.player_b, fs.flashscore_match_id,
                )

            # Guard: if this betting market is already assigned to a
            # DIFFERENT tracked match, skip it instead of crashing on
            # the unique constraint.  (Caused by false-positive name
            # matching — two Flashscore matches matching the same
            # betting-site event.)
            if betting_market_id:
                conflicting = (
                    session.query(TrackedMatch)
                    .filter(
                        TrackedMatch.betting_market_id == betting_market_id,
                        TrackedMatch.flashscore_match_id != fs.flashscore_match_id,
                    )
                    .first()
                )
                if conflicting is not None:
                    logger.warning(
                        "Market %s already assigned to %s (%s vs %s) — "
                        "skipping for %s (%s vs %s)",
                        betting_market_id,
                        conflicting.flashscore_match_id,
                        conflicting.player1_name,
                        conflicting.player2_name,
                        fs.flashscore_match_id,
                        fs.player_a,
                        fs.player_b,
                    )
                    betting_market_id = None

            existing = (
                session.query(TrackedMatch)
                .filter_by(flashscore_match_id=fs.flashscore_match_id)
                .first()
            )

            if existing:
                existing.betting_market_id = betting_market_id
                existing.player1_id = p1.player_id if p1 else None
                existing.player2_id = p2.player_id if p2 else None
                existing.player1_name = fs.player_a
                existing.player2_name = fs.player_b
                existing.tournament = fs.tournament
                existing.scheduled_start = fs.scheduled_start_time
                # When status transitions to a terminal state, record
                # the finish time so the finalizer can use it.
                if existing.status != fs.status and fs.status in (
                    "FINISHED", "RETIRED", "WALKOVER",
                ):
                    existing.actual_finish = (
                        existing.actual_finish
                        or datetime.now(timezone.utc)
                    )
                existing.status = fs.status
                results.append(existing)
            else:
                tm = TrackedMatch(
                    flashscore_match_id=fs.flashscore_match_id,
                    betting_market_id=betting_market_id,
                    player1_id=p1.player_id if p1 else None,
                    player2_id=p2.player_id if p2 else None,
                    player1_name=fs.player_a,
                    player2_name=fs.player_b,
                    tournament=fs.tournament,
                    scheduled_start=fs.scheduled_start_time,
                    status=fs.status,
                )
                session.add(tm)
                results.append(tm)

            if betting_market_id:
                logger.info(
                    "Registered match: %s vs %s (%s) — has odds",
                    fs.player_a, fs.player_b, fs.tournament,
                )
            else:
                logger.info(
                    "Registered match: %s vs %s (%s) — scores only",
                    fs.player_a, fs.player_b, fs.tournament,
                )

        for bt in bt_matches:
            if bt.market_id not in used_bt_market_ids:
                logger.warning(
                    "Betting market %s (%s vs %s) has no matching Flashscore match",
                    bt.market_id, bt.player_a, bt.player_b,
                )

        session.commit()

        for tm in results:
            session.refresh(tm)

    return results
