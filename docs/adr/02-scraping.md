# ADR 2: Scraping Strategy — Why flashscore.mobi

## Problem
Need reliable, parseable HTML for live tennis match data.

## Decision
Use `flashscore.mobi` (mobile site) for score collection instead of `flashscore.com` (desktop SPA).

## Alternatives
- **flashscore.com (desktop)**: Requires JS rendering; Playwright/Selenium adds 500ms+ per page; Headless browser management complexity
- **Official APIs**: No public tennis scoring API exists; third-party APIs are expensive or rate-limited
- **Other bookmaker sites**: More variability, less standard HTML

## Tradeoffs
- + Mobile site returns static HTML — no JS required
- + Fast (200ms per request via httpx)
- + Simple BeautifulSoup parsing
- - Must handle mobile vs desktop HTML differences
- - Flashscore format can change without notice
- - Rate limiting on batch requests (mitigated by CONCURRENCY=8)

## Consequences
- `collector/flashscore/client.py` manages mobile URLs
- Mobile listing parsed in `parser.py`
- Match detail pages fetched for full names + dates
- HTML structure monitored for changes
