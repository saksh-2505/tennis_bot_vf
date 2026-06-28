import logging

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


def get_event_list() -> list[dict]:
    url = f"{BASE_URL}/api/guest/event_list"
    with httpx.Client(headers=HEADERS, timeout=30) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
        return data["data"]["events"]


def get_event_detail(event_id: int) -> dict:
    url = f"{BASE_URL}/api/guest/event/{event_id}"
    with httpx.Client(headers=HEADERS, timeout=30) as client:
        response = client.post(url, json={})
        response.raise_for_status()
        return response.json()["data"]["event"]


def get_market_odds(market_id: str) -> str | None:
    with httpx.Client(headers=HEADERS, timeout=30) as client:
        response = client.post(
            ODDS_URL,
            data={"market_ids[]": market_id},
            headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        data = response.json()
        if data and data[0]:
            return data[0]
        return None
