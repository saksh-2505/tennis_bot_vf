"""Retroactive market matching for historical unmatched matches.

Runs the full 5-signal matcher engine against all finished matches that
never got a betting market assignment.  Can be run as a one-shot script
or scheduled periodically.
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone

from database import SessionLocal
from models.bettingsite import BettingsiteFoundMatch
from models.tracked_match import TrackedMatch
from matcher.engine import match_all

logger = logging.getLogger(__name__)


def run_retroactive_matching(
    min_match_id: int = 0,
    confidence_threshold: float = 0.30,
    dry_run: bool = False,
    limit: int = 0,
) -> dict:
    """Run matching against unmatched finished/expired matches.

    Args:
        min_match_id: Only process matches with id >= this value.
        confidence_threshold: Minimum confidence to accept a match.
        dry_run: If True, report but don't write changes.
        limit: Max matches to process (0 = unlimited).

    Returns:
        Dict with counts: total_scanned, newly_matched, failed, skipped_live.
    """
    stats = {
        "total_scanned": 0,
        "newly_matched": 0,
        "failed": 0,
        "skipped_live": 0,
        "skipped_already_matched": 0,
    }

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

        if not bt_events:
            logger.warning("No betting site events available for matching")
            return stats

        logger.info("Loaded %d betting site events for matching", len(bt_events))

        query = session.query(TrackedMatch).filter(
            TrackedMatch.betting_market_id.is_(None)
        )
        if min_match_id:
            query = query.filter(TrackedMatch.id >= min_match_id)
        if limit:
            query = query.limit(limit)

        unmatched = query.all()

        trackable = []
        for tm in unmatched:
            if tm.status == "LIVE":
                stats["skipped_live"] += 1
                continue
            if tm.betting_market_id:
                stats["skipped_already_matched"] += 1
                continue
            trackable.append(tm)

        stats["total_scanned"] = len(trackable)
        logger.info(
            "Running retroactive matching on %d unmatched non-LIVE matches "
            "(conf >= %.2f, dry_run=%s)",
            len(trackable),
            confidence_threshold,
            dry_run,
        )

        results = match_all(trackable, bt_events, session=session)

        for res in results:
            if res.match_found and res.selected_market_id:
                if res.selected_confidence >= confidence_threshold:
                    for tm in trackable:
                        if tm.flashscore_match_id == res.flashscore_match_id:
                            if not dry_run:
                                tm.betting_market_id = res.selected_market_id
                                tm.market_assigned_at = datetime.now(timezone.utc)
                            stats["newly_matched"] += 1
                            logger.info(
                                "  MATCHED %s vs %s → market %s (%.3f, %s)",
                                tm.player1_name, tm.player2_name,
                                res.selected_market_id,
                                res.selected_confidence,
                                res.selected_confidence_level,
                            )
                            break
                else:
                    logger.debug(
                        "  SKIPPED (low conf %.3f < %.2f): %s vs %s → %s",
                        res.selected_confidence,
                        confidence_threshold,
                        res.flashscore_match_id,
                        res.selected_market_id or "none",
                        res.match_explanation,
                    )
                    stats["failed"] += 1
            else:
                stats["failed"] += 1

        if not dry_run and stats["newly_matched"] > 0:
            try:
                session.commit()
                logger.info("Committed %d new market assignments", stats["newly_matched"])
            except Exception:
                logger.exception("Failed to commit retroactive matches")
                session.rollback()
                stats["newly_matched"] = 0

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retroactive market matching for historical unmatched matches",
    )
    parser.add_argument(
        "--min-match-id", type=int, default=0,
        help="Only process matches with id >= this value",
    )
    parser.add_argument(
        "--confidence-threshold", type=float, default=0.30,
        help="Minimum confidence to accept a match (0.0-1.0, default: 0.30)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would be done without making changes",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Max matches to process (0 = unlimited)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print(f"\nRetroactive Market Matching")
    print(f"  Confidence threshold: {args.confidence_threshold}")
    print(f"  Dry run: {args.dry_run}")
    print(f"  Min match ID: {args.min_match_id}")
    print(f"  Limit: {args.limit or 'unlimited'}\n")

    stats = run_retroactive_matching(
        min_match_id=args.min_match_id,
        confidence_threshold=args.confidence_threshold,
        dry_run=args.dry_run,
        limit=args.limit,
    )

    print(f"\nResults:")
    print(f"  Scanned:            {stats['total_scanned']}")
    print(f"  Newly matched:      {stats['newly_matched']}")
    print(f"  Failed/not matched: {stats['failed']}")
    print(f"  Skipped (LIVE):     {stats['skipped_live']}")
    print(f"  Skipped (has mkt):  {stats['skipped_already_matched']}")

    if stats["total_scanned"] > 0:
        pct = stats["newly_matched"] / stats["total_scanned"] * 100
        print(f"  Match rate:         {pct:.1f}%")

    if args.dry_run and stats["newly_matched"] > 0:
        print("\n[Dry run — no changes written. Remove --dry-run to apply.]")


if __name__ == "__main__":
    main()
