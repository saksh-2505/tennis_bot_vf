# ADR 6: Player Matching — Why Name-Based

## Problem
Need to match player names across Flashscore (abbreviated), Betting Site, and Tennis Explorer (full names).

## Decision
Name-based matching with normalization (uppercase, remove parens, strip accents).

## Alternatives
- **Player ID from Flashscore API**: Flashscore does not expose stable player IDs
- **Tennis Explorer ID lookup**: Requires exact Tennis Explorer URL match
- **Fuzzy matching (Levenshtein)**: Prone to false positives; harder to debug

## Tradeoffs
- + Simple, predictable, testable
- + No external ID dependencies
- + Works across all three data sources
- - Common name aliases (e.g., "RUUD CASPER" vs "CASPER RUUD")
- - Hyphenated names (e.g., "BAUTISTA-AGUT" vs "BAUTISTA AGUT")
- - Missing players in Tennis Explorer generate warnings (not errors)

## Consequences
- `collector/tennis_explorer/__init__.py` handles name normalization
- `registry/service.py` cross-references by `full_name`
- Player warnings are logged but non-blocking
- 227 players currently tracked with 9 failures (unknown names)
