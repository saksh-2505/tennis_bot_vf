# Database Schema

## Technology
TimescaleDB (PostgreSQL 16) with hypertables for time-series data.

## Entity Relationship

```
flashscorefoundmatches           bettingsitefoundmatches
    id (PK)                          id (PK)
    flashscore_match_id (UQ)         market_id (UQ, INDEX)
    player_a                         player_a
    player_b                         player_b
    tournament                       tournament
    scheduled_start_time             odds_data
    status                           discovered_at
    discovered_at
                                      | (matched by player names via registry)
             |                        |
             ▼                        ▼
    tracked_matches
        id (PK)
        flashscore_match_id (UQ, INDEX)
        betting_market_id (UQ, INDEX)
        player1_id → players.player_id
        player2_id → players.player_id
        player1_name
        player2_name
        tournament
        round, surface
        scheduled_start (TIMESTAMPTZ)
        actual_finish (TIMESTAMPTZ)
        match_duration_min
        live_url
        status: DISCOVERED | SCHEDULED | LIVE | FINISHED
        tracking_enabled
             |
             ├── live_scores (hypertable)
             │   tracked_match_id, timestamp, content_hash (composite PK)
             │   set_score_a/b, game_score_a/b
             │   point_score, server, is_tiebreak, match_finished
             │
             ├── live_odds (hypertable)
             │   tracked_match_id, timestamp, content_hash (composite PK)
             │   back_odds_a/b, lay_odds_a/b, volume_a/b
             │
             └── completed_matches
                 id (PK)
                 tracked_match_id (UQ)
                 stats + validation flags

players
    player_id (PK)
    full_name (UQ, INDEX)
    + 40+ profile fields

incidents
    incident_id (PK)
    incident_hash (INDEX)
    severity, status, category, module, title, summary
```

## Hypertable Configuration

Applied in `database.py:init_db()`:

- **chunk_time_interval:** 1 day
- **Compression:** enabled, segment by `tracked_match_id`
- **Compression policy:** compress after 7 days
- **Reorder policy:** by `tracked_match_id`

## Index Strategy

| Table | Index | Purpose |
|-------|-------|---------|
| `tracked_matches` | `flashscore_match_id UNIQUE` | Fast match lookup |
| `tracked_matches` | `betting_market_id UNIQUE` | Fast odds lookup |
| `players` | `full_name UNIQUE` | Dedup on import |
| `flashscorefoundmatches` | `flashscore_match_id UNIQUE` | Dedup during discovery |
| `bettingsitefoundmatches` | `market_id UNIQUE` | Dedup during discovery |
| `incidents` | `incident_hash INDEX` | Dedup on creation |
| `live_scores` | `(tracked_match_id, timestamp, content_hash)` | Dedup hypertable |
| `live_odds` | `(tracked_match_id, timestamp, content_hash)` | Dedup hypertable |

## Foreign Keys

No explicit foreign key constraints exist. All relationships are application-level conventions enforced by the registry and finalizer modules.

## Ownership

| Table | Owner Module | Created By | Modified By |
|-------|-------------|------------|-------------|
| `flashscorefoundmatches` | `collector.flashscore` | Discovery | Discovery (scheduled) |
| `bettingsitefoundmatches` | `collector.betting_site` | Discovery | Discovery (scheduled) |
| `players` | `collector.tennis_explorer` | Discovery | Discovery (scheduled) |
| `tracked_matches` | `registry.service` | Registry | Registry, Live Collector, Finalizer |
| `live_scores` | `live_collector.flashscore_live` | Live Collector | Live Collector (every 10s) |
| `live_odds` | `live_collector.betting_live` | Live Collector | Live Collector (every 2s) |
| `completed_matches` | `finalizer.service` | Finalizer | Finalizer (append-only) |
| `incidents` | `incidents.service` | Incident Monitor | Incident Monitor |

## Migration Strategy

- Schema changes applied via `Base.metadata.create_all()` at startup
- Hypertable conversion via `session.execute()` in `init_db()`
- One-time SQLite→PostgreSQL migration via `migrate_players.py`
- No formal Alembic migrations — schema is additive only
