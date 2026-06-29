# ADR 7: Odds Collection — Why Pipe Parser

## Problem
Betting site API returns odds in a non-standard format requiring custom parsing.

## Decision
Parse odds from a JSON array where the first element is a pipe-delimited market-data string.

## Alternatives
- **Structured JSON API**: Not available from this betting site
- **Selenium/Playwright**: Overkill for data already in the API response
- **Regex extraction**: Less maintainable than field-by-field pipe parsing

## Tradeoffs
- + Works with the only available API format
- + Handles both open markets and closed (`[null]`) markets
- + Retry with backoff on 429/5xx
- - Tight coupling to a specific API response format
- - Multiple market IDs per match require batch requests
- - Empty pipe fields require null-coalescing

## Consequences
- `collector/betting_site/parser.py` contains pipe parsing logic
- `live_collector/betting_live.py` polls per-market-ID
- `[null]` responses are silently skipped
- 1908 odds ticks collected for 4 matches in current deployment
