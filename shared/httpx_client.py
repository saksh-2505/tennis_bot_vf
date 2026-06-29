"""Centralized HTTP client with retry, timeout, and headers."""

import httpx

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


def get_client(**kwargs) -> httpx.Client:
    kwargs.setdefault("headers", HEADERS)
    kwargs.setdefault("timeout", TIMEOUT)
    kwargs.setdefault("follow_redirects", True)
    return httpx.Client(**kwargs)


def get_async_client(**kwargs) -> httpx.AsyncClient:
    kwargs.setdefault("headers", HEADERS)
    kwargs.setdefault("timeout", TIMEOUT)
    kwargs.setdefault("follow_redirects", True)
    return httpx.AsyncClient(**kwargs)
