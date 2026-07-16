"""Retroactive market matching — simplified: delegates to match_all."""
import argparse
import logging
import sys

from database import SessionLocal
from models.bettingsite import BettingsiteFoundMatch
from models.tracked_match import TrackedMatch
from matcher.engine import match_all

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confidence-threshold", type=float, default=0.30)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    with SessionLocal() as session:
        bt_matches = session.query(BettingsiteFoundMatch).all()
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
        logger.info("BT events: %d", len(bt_events))

        query = session.query(TrackedMatch).filter(
            TrackedMatch.betting_market_id.is_(None),
            TrackedMatch.status != "LIVE",
        )
        if args.limit:
            query = query.limit(args.limit)
        unmatched = query.all()
        logger.info("Unmatched non-LIVE: %d", len(unmatched))

        if not unmatched:
            logger.info("All matches already have markets — nothing to do")
            return

        results = match_all(unmatched, bt_events, session=session)
        matched = sum(1 for r in results if r.match_found and r.selected_market_id)
        logger.info("Found: %d/%d matched", matched, len(unmatched))

        if matched:
            if args.dry_run:
                logger.info("[DRY RUN - no changes written]")
                session.rollback()
            else:
                try:
                    session.commit()
                    logger.info("Committed %d new market assignments", matched)
                except Exception as e:
                    logger.error("Commit failed: %s", e)
                    session.rollback()


if __name__ == "__main__":
    main()
