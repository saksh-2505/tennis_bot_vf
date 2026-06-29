# ADR 1: Storage — Why TimescaleDB

## Problem
Need a database that handles both relational (matches, players, incidents) and time-series (live scores, odds) data with efficient historical queries.

## Decision
TimescaleDB (PostgreSQL 16) — standard PostgreSQL for relational data + hypertables for time-series.

## Alternatives
- **Plain PostgreSQL**: Good for relational, poor for time-series (no auto-partitioning, slow range scans)
- **InfluxDB**: Excellent time-series but lacks JOINs and relational features
- **DuckDB + SQLite**: Simpler but no server mode, no concurrent access

## Tradeoffs
- + Single database for all data types
- + Hypertables auto-partition by time
- + Native compression policies
- + Full SQL support
- - Requires specific Docker image
- - TimescaleDB-specific features add complexity

## Consequences
- Hypertable configuration in `database.py:init_db()`
- Compression + reorder policies for live_scores/live_odds
- No foreign keys enforced at DB level (application-level only)
