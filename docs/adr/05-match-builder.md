# ADR 5: Match Builder — Why Registry Pattern

## Problem
Need to deduplicate and cross-reference matches from two sources (Flashscore + Betting Site).

## Decision
Registry pattern: `build_match_registry()` reads both source tables and creates/updates `tracked_matches`.

## Alternatives
- **Direct merge in collector**: Couples collectors; hard to audit
- **SQL MERGE statement**: Database-specific; less testable
- **ETL pipeline**: Overengineered for current scale

## Tradeoffs
- + Centralized matching logic in one module
- + Testable in isolation (in-memory SQLite)
- + Each discovery cycle reconciles data
- - Runs synchronously during discovery (locks registry table)
- - Requires both source tables to be populated first

## Consequences
- `registry/service.py` is the single source of truth for match state
- Matches without betting market get `betting_market_id=NULL` (scores-only)
- Betting markets without Flashscore match are logged as warnings
- Player matching is name-based with Tennis Explorer lookup
