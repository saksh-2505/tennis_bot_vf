"""Match registry. Cross-references Flashscore matches with Betting Site markets."""
import logging
from typing import TYPE_CHECKING

from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import engine

if TYPE_CHECKING:
    from models.tracked_match import TrackedMatch

logger = logging.getLogger(__name__)


def _find_player(session, name: str):
    """Look up a player by name, trying multiple formats.

    Flashscore names are "FIRST LAST" (e.g. "SVAJDA Z"), while the
    players table stores "LAST FIRST" (e.g. "SVAJDA ZIZOU").  Try
    exact match, reversed order, and last-name partial match.
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

        last = parts[-1]
        if len(last) >= 3:
            p = session.query(Player).filter(
                or_(
                    Player.full_name.ilike(f"{last} %"),
                    Player.full_name.ilike(f"% {last}"),
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

        bt_by_players: dict[tuple[str, str], list[BettingsiteFoundMatch]] = {}
        for bt in bt_matches:
            key = (bt.player_a, bt.player_b)
            bt_by_players.setdefault(key, []).append(bt)

        used_bt_market_ids: set[str] = set()

        for fs in fs_matches:
            candidates: list[BettingsiteFoundMatch] = []
            key1 = (fs.player_a, fs.player_b)
            key2 = (fs.player_b, fs.player_a)

            candidates.extend(bt_by_players.get(key1, []))
            candidates.extend(bt_by_players.get(key2, []))

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
