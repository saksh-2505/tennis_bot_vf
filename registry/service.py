import logging
from typing import TYPE_CHECKING

from database import engine

if TYPE_CHECKING:
    from models.tracked_match import TrackedMatch

logger = logging.getLogger(__name__)


def build_match_registry() -> list["TrackedMatch"]:
    import database as db

    from models.bettingsite import BettingsiteFoundMatch
    from models.flashscore import FlashscoreFoundMatch
    from models.player import Player
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

            if not candidates:
                logger.warning(
                    "Flashscore match %s (%s vs %s) has no matching betting market — skipping",
                    fs.flashscore_match_id, fs.player_a, fs.player_b,
                )
                continue

            if len(candidates) > 1:
                logger.error(
                    "Flashscore match %s (%s vs %s) has %d matching betting markets — skipping",
                    fs.flashscore_match_id, fs.player_a, fs.player_b, len(candidates),
                )
                continue

            bt = candidates[0]
            used_bt_market_ids.add(bt.market_id)

            p1 = session.query(Player).filter_by(full_name=fs.player_a).first()
            p2 = session.query(Player).filter_by(full_name=fs.player_b).first()

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
                existing.betting_market_id = bt.market_id
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
                    betting_market_id=bt.market_id,
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

            logger.info(
                "Registered match: %s vs %s (%s)",
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
