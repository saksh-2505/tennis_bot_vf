import hashlib
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
            for o in [self.back_odds_a, self.back_odds_b, self.lay_odds_a, self.lay_odds_b]
        )

    def content_hash(self) -> str:
        values = (
            f"{self.back_odds_a},{self.back_odds_b},"
            f"{self.lay_odds_a},{self.lay_odds_b}"
        )
        return hashlib.sha256(values.encode()).hexdigest()


def poll_betting_odds(market_id: str) -> OddsSnapshot:
    """Fetch live odds from the betting API and return a snapshot.

    The API returns a pipe-delimited string. We try to extract back and
    lay odds for both runners.  At least one odds value must be non-None
    for the tick to be logged.
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
            return _parse_odds_pipe(resp.text)
    except Exception:
        logger.debug("Odds poll failed for market %s", market_id)
        return OddsSnapshot()


def _parse_odds_pipe(data: str) -> OddsSnapshot:
    if not data or not data.strip():
        return OddsSnapshot()

    parts = data.split("|")
    result = OddsSnapshot()

    selections: dict[int, float | None] = {}
    selection_id = 0

    idx = 1
    while idx < len(parts) - 2:
        if not parts[idx].replace(".", "").isdigit():
            idx += 1
            continue
        idx += 1

        sid_str = ""
        while idx < len(parts):
            token = parts[idx]
            if token in ("ACTIVE", "SUSPENDED", "REMOVED", "LOSER", "WINNER"):
                idx += 1
                break
            if token.isdigit() and len(token) >= 6:
                sid_str = token
                idx += 1
                if idx < len(parts) and parts[idx] in (
                    "ACTIVE", "SUSPENDED", "REMOVED", "LOSER", "WINNER",
                ):
                    idx += 1
                    break
            idx += 1
        else:
            break

        if sid_str:
            try:
                sid = int(sid_str)
            except ValueError:
                continue
        else:
            continue

        back_odds = None
        lay_odds = None
        while idx < len(parts):
            try:
                val = float(parts[idx])
                if back_odds is None:
                    back_odds = val
                elif lay_odds is None:
                    lay_odds = val
                    break
                else:
                    break
            except ValueError:
                break
            idx += 1

        selections[sid] = back_odds

    sids = sorted(selections.keys())
    if len(sids) >= 1:
        result.back_odds_a = selections.get(sids[0])
    if len(sids) >= 2:
        result.back_odds_b = selections.get(sids[1])

    return result
