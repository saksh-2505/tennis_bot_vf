"""HTTP client for flashscore.mobi."""
import logging

import httpx

logger = logging.getLogger(__name__)

MOBILE_LISTING_URL = "https://www.flashscore.mobi/tennis/"
MOBILE_MATCH_URL = "https://www.flashscore.mobi/match/{match_id}/"
DESKTOP_MATCH_URL = "https://www.flashscore.com/match/{match_id}/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT = 30.0
CONCURRENCY = 8


def fetch_mobile_listing() -> str:
    with httpx.Client(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
        response = client.get(MOBILE_LISTING_URL)
        response.raise_for_status()
        return response.text


def fetch_match_details(match_id: str) -> str:
    url = MOBILE_MATCH_URL.format(match_id=match_id)
    with httpx.Client(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


async def fetch_match_details_batch(
    match_ids: list[str],
) -> dict[str, str]:
    results: dict[str, str] = {}

    async def fetch_one(client: httpx.AsyncClient, match_id: str) -> None:
        url = MOBILE_MATCH_URL.format(match_id=match_id)
        try:
            response = await client.get(url)
            response.raise_for_status()
            results[match_id] = response.text
        except Exception:
            logger.warning("Failed to fetch details for match %s", match_id)

    limits = httpx.Limits(max_connections=CONCURRENCY)
    async with httpx.AsyncClient(
        headers=HEADERS, timeout=TIMEOUT, follow_redirects=True, limits=limits
    ) as client:
        import asyncio

        tasks = [fetch_one(client, mid) for mid in match_ids]
        await asyncio.gather(*tasks)

    return results
