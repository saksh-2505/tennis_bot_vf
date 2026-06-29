"""HTTP client for tennisexplorer.com."""
import logging

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://www.tennisexplorer.com"
SEARCH_URL = f"{BASE_URL}/res/ajax/search.php"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": f"{BASE_URL}/",
}


def search_player(name: str) -> dict | None:
    params = {"s": name, "t": "p", "all": "1"}
    with httpx.Client(headers=HEADERS, timeout=30) as client:
        response = client.get(SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()

    if data.get("nodata") or data.get("toomuch"):
        return None

    links = data.get("links", [])
    if not links:
        return None

    if len(links) == 1:
        return links[0]

    for link in links:
        link_name = link["name"].lower()
        query_lower = name.lower()
        query_parts = query_lower.split()
        if all(part in link_name for part in query_parts):
            return link

    return links[0]


def fetch_player_profile(url_path: str) -> str:
    url = f"{BASE_URL}/player/{url_path}/"
    with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text
