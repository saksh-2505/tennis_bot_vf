"""Live betting odds scraper for a single market."""
import hashlib
import json
import logging
from dataclasses import dataclass

import httpx

from config import settings

logger = logging.getLogger(__name__)

ODDS_URL = "https://odd.ocric99.com/ws/getMarketDataNew"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/x-www-form-urlencoded",
}

TIMEOUT = 30.0

STATUS_TOKENS = {"ACTIVE", "SUSPENDED", "REMOVED", "LOSER", "WINNER", "BALL_RUNNING", "OPEN"}


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

    # The first element is the market-data pipe string
    market_pipe = data[0]
    if not isinstance(market_pipe, str) or not market_pipe.strip():
        logger.debug("No market data pipe for market %s", market_id)
        return OddsSnapshot()

    # Check for null response
    # The API returns "null" or "[null]" for closed/unavailable markets
    if market_pipe.strip() in ("null", "None", ""):
        logger.debug("Null market data for market %s (possibly closed)", market_id)
        return OddsSnapshot()

    return _parse_odds_pipe(market_pipe, market_id)


def _parse_odds_pipe(market_pipe: str, market_id: str) -> OddsSnapshot:
    """Parse a pipe-delimited market-data string into OddsSnapshot.

    Pipe format (simplified):
      market_id||OPEN|...|selection_id_a|ACTIVE|back_price_1|volume_1|back_price_2|volume_2|...|selection_id_b|ACTIVE|back_price_1|volume_1|...

    Only the BEST (first) back price is used for each selection.
    Lay odds and volumes are not available from this API and remain None.
    """
    result = OddsSnapshot()
    parts = market_pipe.split("|")

    selections: list[float | None] = []

    i = 0
    while i < len(parts):
        token = parts[i]

        # Look for selection IDs (6+ digit numbers)
        if token.lstrip("-").isdigit() and len(token) >= 6:
            sid = int(token)
            i += 1

            # Skip status tokens
            while i < len(parts) and parts[i] in STATUS_TOKENS:
                i += 1

            # Read first back price (the best available)
            if i < len(parts):
                try:
                    back_odds = float(parts[i])
                    if back_odds > 0:
                        selections.append(back_odds)
                except ValueError:
                    pass
                i += 1

                # Skip the volume for this price level (we only track best price)
                try:
                    float(parts[i])
                    i += 1
                except ValueError:
                    pass

            continue

        i += 1

    if len(selections) >= 1:
        result.back_odds_a = selections[0]
    if len(selections) >= 2:
        result.back_odds_b = selections[1]

    if not selections:
        logger.debug("No odds selections found in pipe for market %s", market_id)

    return result
