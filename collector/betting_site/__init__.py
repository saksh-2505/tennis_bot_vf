import logging

from database import SessionLocal, engine
from models.bettingsite import BettingsiteFoundMatch

from .client import get_event_detail, get_event_list, get_market_odds
from .parser import (
    BettingsiteMatch,
    filter_tennis_matches,
    match_events_to_flashscore,
    parse_odds_for_runners,
)

logger = logging.getLogger(__name__)

MATCH_URL_TEMPLATE = "https://reddybook.green/sports/detail/{event_id}"


def discover_matches(
    flashscore_matches: list,
) -> list[BettingsiteMatch]:
    events = get_event_list()
    logger.info("Fetched %d total events from betting site API", len(events))

    tennis_events = filter_tennis_matches(events)
    logger.info(
        "Filtered to %d tennis match events: %s",
        len(tennis_events),
        [e["name"] for e in tennis_events],
    )

    pairs = match_events_to_flashscore(tennis_events, flashscore_matches)
    logger.info("Matched %d events to Flashscore matches", len(pairs))

    matches: list[BettingsiteMatch] = []

    for event, fs_match in pairs:
        event_id = event["event_id"]
        event_name = event["name"]

        detail = get_event_detail(event_id)
        match_odds = detail.get("match_odds")
        if not match_odds:
            logger.info("No match_odds for event %d (%s) — skipping", event_id, event_name)
            continue

        market_id = match_odds["market_id"]
        runners = match_odds.get("runners", [])

        if len(runners) < 2:
            logger.info("Less than 2 runners for event %d — skipping", event_id)
            continue

        runner_a = runners[0]
        runner_b = runners[1]

        odds_pipe = get_market_odds(market_id)
        odds_a, odds_b = parse_odds_for_runners(
            odds_pipe, runner_a["selection_id"], runner_b["selection_id"]
        )

        if odds_a is None and odds_b is None:
            logger.info("No odds available for event %d (%s) — skipping", event_id, event_name)
            continue

        match_url = MATCH_URL_TEMPLATE.format(event_id=event_id)

        matches.append(
            BettingsiteMatch(
                market_id=market_id,
                match_url=match_url,
                player_a=runner_a["name"].upper(),
                player_b=runner_b["name"].upper(),
                odds_player_a=odds_a,
                odds_player_b=odds_b,
            )
        )

    logger.info(
        "Discovered %d betting site matches with odds: %s",
        len(matches),
        [
            f"{m.player_a} ({m.odds_player_a}) vs {m.player_b} ({m.odds_player_b})"
            for m in matches
        ],
    )

    return matches


def save_matches_to_db(matches: list[BettingsiteMatch]) -> int:
    BettingsiteFoundMatch.metadata.create_all(bind=engine)

    saved = 0
    with SessionLocal() as session:
        for m in matches:
            existing = (
                session.query(BettingsiteFoundMatch)
                .filter_by(market_id=m.market_id)
                .first()
            )
            if existing:
                continue

            record = BettingsiteFoundMatch(
                market_id=m.market_id,
                match_url=m.match_url,
                player_a=m.player_a,
                player_b=m.player_b,
                odds_player_a=m.odds_player_a,
                odds_player_b=m.odds_player_b,
                discovered_at=m.discovered_at,
            )
            session.add(record)
            saved += 1

        session.commit()

    logger.info("Saved %d new matches to bettingsitefoundmatches table", saved)
    return saved
