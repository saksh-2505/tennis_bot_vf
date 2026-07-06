"""Live betting odds scraper for a single market."""
import hashlib
import json
import logging
from dataclasses import dataclass

import httpx

from config import settings

logger = logging.getLogger(__name__)

ODDS_URL = "https://odd.ocric99.com/ws/getMarketDataNew"
SITE_URL = "https://reddybook.green"

HEADERS = {
    "Origin": SITE_URL,
    "Referer": f"{SITE_URL}/",
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded",
}

TIMEOUT = 30.0


@dataclass
class OddsSnapshot:
    back_odds_a: float | None = None
    back_odds_b: float | None = None
    lay_odds_a: float | None = None
    lay_odds_b: float | None = None
    volume_a: float | None = None
    volume_b: float | None = None

    def any_valid(self) -> bool:
        return any(
            o is not None
            for o in [self.back_odds_a, self.back_odds_b]
        )

    def content_hash(self) -> str:
        values = (
            f"{self.back_odds_a},{self.back_odds_b},"
            f"{self.lay_odds_a},{self.lay_odds_b}"
        )
        return hashlib.sha256(values.encode()).hexdigest()


def poll_betting_odds(market_id: str) -> OddsSnapshot:
    """Fetch live odds from the betting API and return a snapshot.

    The API returns a JSON array. The first element is a pipe-delimited
    market-data string that contains back-odds levels for each selection
    (runner).  We extract only the best available back odds for the first
    two runners and ignore lay odds (not present in this API).
    """
    try:
        with httpx.Client(
            headers=HEADERS, timeout=TIMEOUT, follow_redirects=True
        ) as client:
            resp = client.post(
                ODDS_URL,
                data={"market_ids[]": market_id},
            )
            resp.raise_for_status()
            return _parse_odds_response(resp.text, market_id)
    except httpx.HTTPStatusError as e:
        logger.warning("Odds HTTP error for market %s: %d", market_id, e.response.status_code)
    except Exception as e:
        logger.debug("Odds poll failed for market %s: %s", market_id, e)
    return OddsSnapshot()


def _parse_odds_response(body: str, market_id: str) -> OddsSnapshot:
    """Parse the JSON array response from the odds API."""
    if not body or not body.strip():
        logger.debug("Empty odds response for market %s", market_id)
        return OddsSnapshot()

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON odds response for market %s", market_id)
        return OddsSnapshot()

    if not isinstance(data, list) or len(data) == 0:
        logger.debug("No data in odds response for market %s", market_id)
        return OddsSnapshot()

    market_pipe = data[0]
    if market_pipe is None or (isinstance(market_pipe, str) and market_pipe.strip() in ("null", "None", "")):
        logger.debug("Null market data for market %s (possibly closed)", market_id)
        return OddsSnapshot()

    if not isinstance(market_pipe, str) or not market_pipe.strip():
        logger.debug("No market data pipe for market %s", market_id)
        return OddsSnapshot()

    return _parse_odds_pipe_snapshot(market_pipe, market_id)


def _parse_odds_pipe_snapshot(market_pipe: str, market_id: str) -> OddsSnapshot:
    """Parse a pipe-delimited market-data string into OddsSnapshot.

    Reuses the battle-tested ``parse_odds_pipe`` from the collector module
    which handles the full pipe format including edge cases like SUSPENDED,
    multiple status tokens, and float-valued tokens between selection IDs.
    """
    from collector.betting_site.parser import parse_odds_pipe

    result = OddsSnapshot()
    try:
        odds_map = parse_odds_pipe(market_pipe)
    except Exception:
        logger.warning("Failed to parse odds pipe for market %s", market_id, exc_info=True)
        return result

    sel_ids = list(odds_map.keys())
    if len(sel_ids) >= 1:
        result.back_odds_a = odds_map[sel_ids[0]]
    if len(sel_ids) >= 2:
        result.back_odds_b = odds_map[sel_ids[1]]

    if not odds_map:
        logger.debug("No odds selections found in pipe for market %s", market_id)

    return result
