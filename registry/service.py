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

        if len(last_name) >= 2:
            if len(last_name) >= 4:
                p = session.query(Player).filter(
                    or_(
                        Player.full_name.ilike(f"{last_name} %"),
                        Player.full_name.ilike(f"% {last_name}"),
                        Player.full_name.ilike(f"%{last_name}%"),
                    )
                ).first()
            else:
                p = session.query(Player).filter(
                    or_(
                        Player.full_name.ilike(f"{last_name} %"),
                        Player.full_name.ilike(f"% {last_name}"),
                        Player.full_name.ilike(f"% {last_name} %"),
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
    from matcher.engine import match_all

    TrackedMatch.metadata.create_all(bind=engine)

    results: list[TrackedMatch] = []

    with db.SessionLocal() as session:
        fs_matches = session.query(FlashscoreFoundMatch).all()
        bt_matches = session.query(BettingsiteFoundMatch).all()

        existing_tracked = {
            tm.flashscore_match_id: tm
            for tm in session.query(TrackedMatch).all()
        }

        bt_events = [
            {
                "name": f"{bt.player_a} v {bt.player_b}",
                "market_id": bt.market_id,
                "runner_a": bt.player_a,
                "runner_b": bt.player_b,
                "date": bt.event_date or "",
                "comp_name": bt.comp_name or "",
            }
            for bt in bt_matches
        ]

        trackable = []
        for fs in fs_matches:
            tm = existing_tracked.get(fs.flashscore_match_id)
            if tm is None:
                player1_id = None
                player2_id = None
                p1 = _find_player(session, fs.player_a)
                p2 = _find_player(session, fs.player_b)
                if p1:
                    player1_id = p1.player_id
                if p2:
                    player2_id = p2.player_id

                tm = TrackedMatch(
                    flashscore_match_id=fs.flashscore_match_id,
                    betting_market_id=None,
                    player1_id=player1_id,
                    player2_id=player2_id,
                    player1_name=fs.player_a,
                    player2_name=fs.player_b,
                    tournament=fs.tournament,
                    scheduled_start=fs.scheduled_start_time,
                    status=fs.status,
                )
                session.add(tm)
                session.flush()
                results.append(tm)
            else:
                if fs.status != tm.status and fs.status in ("FINISHED", "RETIRED", "WALKOVER"):
                    tm.actual_finish = tm.actual_finish or datetime.now(timezone.utc)
                if tm.status != "FINISHED":
                    tm.status = fs.status
                tm.player1_name = fs.player_a
                tm.player2_name = fs.player_b
                tm.tournament = fs.tournament
                tm.scheduled_start = fs.scheduled_start_time
                results.append(tm)

            trackable.append(tm)

        try:
            session.commit()
        except Exception as exc:
            logger.exception("Failed to commit tracked matches before matching: %s", exc)
            session.rollback()
            return results

        match_results = match_all(trackable, bt_events, session=session)

        for res in match_results:
            if res.match_found and res.selected_market_id:
                for tm in trackable:
                    if tm.flashscore_match_id == res.flashscore_match_id:
                        if tm.betting_market_id != res.selected_market_id:
                            tm.betting_market_id = res.selected_market_id
                            tm.market_assigned_at = datetime.now(timezone.utc)
                        break

        try:
            session.commit()
        except Exception as exc:
            logger.exception("Failed to commit market assignments: %s", exc)
            session.rollback()

        for tm in trackable:
            session.refresh(tm)

        assigned = sum(1 for r in match_results if r.match_found)
        logger.info(
            "Registry: %d tracked matches, %d assigned to betting markets "
            "(%d unmatched)",
            len(trackable), assigned, len(trackable) - assigned,
        )

    return results
