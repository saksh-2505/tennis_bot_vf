# ADR 3: Database Schema — Why No Foreign Keys

## Problem
Performance, deployment simplicity, and migration flexibility for schema management.

## Decision
Use application-level conventions instead of DB-level foreign keys.

## Alternatives
- **Explicit FK constraints**: Normal practice for relational integrity, but schema changes require migration tooling
- **Alembic migrations**: Adds complexity; schema changes during live deployment require careful sequencing

## Tradeoffs
- + Faster inserts (no FK checks)
- + Easier schema evolution (no constraint conflicts)
- + Simpler deployment (no migration runs)
- - No DB-level integrity enforcement
- - Orphan records possible on crashes
- - Testing must validate referential integrity

## Consequences
- `registry/service.py` is the authoritative cross-reference
- All `tracked_match_id` references are application-enforced
- `finalizer/service.py` checks `AlreadyFinalized` explicitly
- Regular incident checks verify data consistency
