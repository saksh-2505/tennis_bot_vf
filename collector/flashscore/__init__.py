"""Flashscore discovery pipeline and DB persistence."""
import asyncio
import logging
from datetime import datetime, timezone

from database import SessionLocal, engine
from models.flashscore import FlashscoreFoundMatch

from .client import fetch_match_details, fetch_mobile_listing
from .parser import (
    Match,
    RawMatch,
    build_match,
    extract_full_names_from_title,
    extract_match_date_from_title,
    extract_match_datetime,
    filter_singles,
    parse_mobile_listing,
)

logger = logging.getLogger(__name__)


def discover_matches() -> list[Match]:
    html = fetch_mobile_listing()
    raw_matches = parse_mobile_listing(html)
    logger.info("Found %d total matches on mobile listing", len(raw_matches))

    singles = filter_singles(raw_matches)
    logger.info("Filtered to %d ATP/WTA/Challenger singles matches", len(singles))

    matches = _enrich_with_full_names(singles)

    logger.info(
        "Discovered %d singles matches: %s",
        len(matches),
        [
            f"{m.player_a} vs {m.player_b} ({m.tournament})"
            for m in matches
        ],
    )

    return matches


def save_matches_to_db(matches: list[Match]) -> int:
    from models.flashscore import FlashscoreFoundMatch

    FlashscoreFoundMatch.metadata.create_all(bind=engine)

    saved = 0
    updated = 0
    with SessionLocal() as session:
        for m in matches:
            existing = (
                session.query(FlashscoreFoundMatch)
                .filter_by(flashscore_match_id=m.flashscore_match_id)
                .first()
            )
            if existing:
                if m.scheduled_start_time is not None and existing.scheduled_start_time != m.scheduled_start_time:
                    existing.scheduled_start_time = m.scheduled_start_time
                if existing.status != m.status:
                    existing.status = m.status
                updated += 1
                continue

            record = FlashscoreFoundMatch(
                flashscore_match_id=m.flashscore_match_id,
                tournament=m.tournament,
                player_a=m.player_a,
                player_b=m.player_b,
                scheduled_start_time=m.scheduled_start_time,
                status=m.status,
                discovered_at=m.discovered_at,
            )
            session.add(record)
            saved += 1

        session.commit()

    logger.info(
        "Saved %d new, updated %d existing in flashscorefoundmatches table",
        saved, updated,
    )
    return saved


def _enrich_with_full_names(raw_matches: list[RawMatch]) -> list[Match]:
    match_ids = [m.flashscore_match_id for m in raw_matches]
    matches: list[Match] = []

    if len(raw_matches) <= 3:
        for raw in raw_matches:
            detail_html = fetch_match_details(raw.flashscore_match_id)
            full_names = extract_full_names_from_title(detail_html)
            detail_dt = extract_match_datetime(detail_html) if detail_html else None
            match_date = None
            if detail_dt is None and detail_html:
                match_date = extract_match_date_from_title(detail_html)
            matches.append(build_match(raw, full_names, match_date, detail_dt))
    else:
        results = asyncio.run(
            _fetch_details_async(raw_matches)
        )

        for raw in raw_matches:
            sid = raw.flashscore_match_id
            detail_html = results.get(sid)
            full_names = None
            match_date = None
            detail_dt = None
            if detail_html:
                full_names = extract_full_names_from_title(detail_html)
                detail_dt = extract_match_datetime(detail_html)
                if detail_dt is None:
                    match_date = extract_match_date_from_title(detail_html)
            matches.append(build_match(raw, full_names, match_date, detail_dt))

    return matches


async def _fetch_details_async(
    raw_matches: list[RawMatch],
) -> dict[str, str]:
    from .client import fetch_match_details_batch

    match_ids = [m.flashscore_match_id for m in raw_matches]
    return await fetch_match_details_batch(match_ids)
