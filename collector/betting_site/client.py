"""HTTP client for betting site with retry/backoff."""
import logging
import time

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.dcric99.com"
ODDS_URL = "https://odd.ocric99.com/ws/getMarketDataNew"
SITE_URL = "https://reddybook.green"

HEADERS = {
    "Origin": SITE_URL,
    "Referer": f"{SITE_URL}/",
    "Accept": "application/json",
}

_MAX_RETRIES = 3
_RETRY_BACKOFF = 5.0


def _request(method: str, url: str, **kwargs) -> httpx.Response:
    """Make an HTTP request with automatic retry on 429/5xx."""
    for attempt in range(_MAX_RETRIES):
        with httpx.Client(headers=HEADERS, timeout=30) as client:
            try:
                response = client.request(method, url, **kwargs)
                if response.status_code == 429 and attempt < _MAX_RETRIES - 1:
                    wait = _RETRY_BACKOFF * (attempt + 1)
                    logger.warning("Rate limited on %s — retrying in %.0fs (attempt %d/%d)",
                                   url, wait, attempt + 1, _MAX_RETRIES)
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 502, 503, 504) and attempt < _MAX_RETRIES - 1:
                    wait = _RETRY_BACKOFF * (attempt + 1)
                    logger.warning("HTTP %d on %s — retrying in %.0fs (attempt %d/%d)",
                                   e.response.status_code, url, wait, attempt + 1, _MAX_RETRIES)
                    time.sleep(wait)
                    continue
                raise
    raise httpx.HTTPStatusError(f"All {_MAX_RETRIES} retries exhausted", request=None, response=None)


def get_event_list() -> list[dict]:
    url = f"{BASE_URL}/api/guest/event_list"
    response = _request("GET", url)
    return response.json()["data"]["events"]


def get_event_detail(event_id: int) -> dict:
    url = f"{BASE_URL}/api/guest/event/{event_id}"
    response = _request("POST", url, json={})
    return response.json()["data"]["event"]


def get_market_odds(market_id: str) -> str | None:
    response = _request(
        "POST",
        ODDS_URL,
        data={"market_ids[]": market_id},
        headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
    )
    data = response.json()
    if data and data[0]:
        return data[0]
    return None
