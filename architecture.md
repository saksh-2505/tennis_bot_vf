# Sports Trading Platform V3 — Architecture

## 1. Project Overview

Live tennis data collection, replay, research, backtesting, and execution platform.

**Stack:** Python >=3.12, SQLAlchemy 2.x, httpx, BeautifulSoup4, Pydantic Settings, TimescaleDB (PostgreSQL 16)

**Current Status:** Phase 1 (Match Discovery) complete. Phase 2.0 (Match Registry) complete. Phase 2.1 (Discovery Orchestrator) complete. Phase 2 (Live Data Collection) built. Phase 2.2 (Match Finalizer) built — `completed_matches` table, stats/validation pipeline. Phases 3–10 are stubbed.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         main.py                                      │
│              setup_logging() → check_connection() → init_db()        │
│                    └── run_platform()                                 │
└────────────────────────┬────────────────────────────────────────────┘
                         │
          ┌──────────────┴────────────────────┐
          ▼                                   ▼
┌──────────────────────┐         ┌──────────────────────────────────┐
│  MAIN THREAD          │         │  BACKGROUND THREAD (daemon)       │
│  run_platform()       │         │  run_live_collection_loop()       │
│                       │         │                                   │
│  ∞ forever:           │         │  ∞ forever:                       │
│  ├── status monitor   │         │  ├── find LIVE matches            │
│  ├── scheduled disc.  │         │  ├── asyncio.gather(              │
│  └── pre-fetch URLs   │         │  │     poll_flashscore()           │
└──────────┬────────────┘         │  │     poll_betting()             │
           │                      │  │   )                            │
           │                      │  └── batch INSERT ... ON CONFLICT │
           │                      │                                   │
           └──────────┬───────────┘                                   │
                      ▼                                               │
┌────────────────────────────────────────────────────────────────────┐
│                        TIMESCALEDB (PostgreSQL 16)                  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  Regular tables: flashscorefoundmatches, bettingsitefoundmatches│
│  │  players, tracked_matches                                      │ │
│  └───────────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  Hypertables: live_scores, live_odds                          │ │
│  │  chunk_interval=1d, compression=7d, retention=infinite        │ │
│  │  UNIQUE (tracked_match_id, timestamp, content_hash)           │ │
│  └───────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
┌─────────────────┐ ┌──────────┐ ┌──────────────────┐
│  Flashscore      │ │ Betting  │ │ Tennis Explorer  │
│  Collector       │ │ Site     │ │ Collector        │
│                  │ │ Collector│ │                  │
│  fetch_listing() │ │          │ │ search_player()  │
│  parse_mobile()  │ │ event_list()  │ fetch_profile() │
│  filter_singles()│ │ filter() │ │ parse_profile()  │
│  enrich_names()  │ │ match()  │ │                  │
│  save_matches()  │ │ odds()   │ │ upsert_player()  │
│                  │ │ save()   │ │                  │
└────────┬─────────┘ └────┬─────┘ └────────┬─────────┘
          │                │                 │
          ▼                ▼                 ▼
┌───────────────────────────────────────────────────────────────┐
│                    TIMESCALEDB (PostgreSQL 16)                  │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Regular tables:                                        │  │
│  │  flashscorefoundmatches, bettingsitefoundmatches,        │  │
│  │  players, tracked_matches                                │  │
│  └──────────┬──────────────────────────────────────────────┘  │
│             │                                                 │
│  ┌──────────▼──────────────────────────────────────────────┐  │
│  │  Hypertables: live_scores, live_odds                    │  │
│  │  chunk_interval=1d, compression=7d, retention=infinite  │  │
│  └─────────────────────────────────────────────────────────┘  │
│             │                                                 │
│  ┌──────────▼──────────────────────────────────────────────┐  │
│  │  match_registry: tracked_matches                        │  │
│  │  (cross-reference by player names, resolve player IDs)  │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

---

## 3. Data Pipeline

### Phase 1 — Flashscore Discovery

```
flashscore.mobi/tennis/
        │
        ▼
  fetch_mobile_listing()        sync GET, returns HTML
        │
        ▼
  parse_mobile_listing()        BeautifulSoup parse: tournaments, matches, times, statuses
        │
        ▼
  filter_singles()              keeps only ATP/WTA/Challenger singles
        │
        ▼
  enrich_with_full_names()      fetch match detail pages (sync for ≤3, async batch for >3)
        │                        extract full names + date from <title> tag
        ▼
  build_match()                  combine raw + full names → Match dataclass
        │
        ▼
  save_matches_to_db()           deduplicate by flashscore_match_id → INSERT
```

**Key types:**
- `RawMatch` — raw parsed data: id, tournament, abbreviated names, time string, status
- `Match` — enriched: full names (uppercased), parsed datetime, discovered_at

**Client constants:**
- `MOBILE_LISTING_URL = "https://flashscore.mobi/tennis/"`
- `CONCURRENCY = 8` (async detail fetches)

### Phase 2 — Betting Site Odds

```
api.dcric99.com/guest/event_list
        │
        ▼
  get_event_list()              sync GET → list of event dicts
        │
        ▼
  filter_tennis_matches()       event_type_id == 2 AND name contains " v "
        │
        ▼
  match_events_to_flashscore()  fuzzy match by last name (prefix 5 chars, exact for ≤4)
        │                        each event/match used once
        ▼
  get_event_detail()             POST → event detail (runners, market_ids, selection IDs)
        │
        ▼
  get_market_odds()              POST to odd.ocric99.com → pipe-delimited odds string
        │
        ▼
  parse_odds_for_runners()       extract back odds for each runner from pipe data
        │
        ▼
  save_matches_to_db()           deduplicate by market_id → INSERT
```

**Key types:**
- `BettingsiteMatch` — `market_id`, `match_url`, `player_a`, `player_b`, `odds_player_a`, `odds_player_b`, `discovered_at`

**Fuzzy matching strategy:**
- Extract last name from Flashscore `Match.player_a` / `.player_b`
- For compound last names (e.g., "DE MINAUR"), try all combinations
- Single words ≤4 chars: exact match required
- Words ≥5 chars: first 5 char prefix match
- Event name like "Novak Djokovic v Jannik Sinner" → match "DJOKOVIC" and "SINNER"

### Phase 3 — Player Enrichment

```
TennisExplorer search API
        │
        ▼
  search_player(name)           GET search → best matching player link
        │
        ▼
  fetch_player_profile()        GET /player/{path}/ → HTML
        │
        ▼
  parse_player_profile()        BeautifulSoup → PlayerData (45+ fields)
        │
        ▼
  upsert_player()                INSERT or UPDATE (non-None fields only)
```

**Parsed fields (PlayerData):**
- **Identity:** full_name, first_name, last_name, nationality, date_of_birth, age, height, weight, plays, backhand, gender, atp_or_wta, profile_url
- **Rankings:** current_rank, career_high_rank, ranking_points
- **Career W/L:** total_matches, total_wins, total_losses, career_win_percentage
- **Per-surface W/L:** clay/hard/grass/indoor — matches, wins, losses, win_percentage
- **Serve/Return:** first_serve_percentage, first_serve_points_won, second_serve_points_won, service_games_won, break_points_saved, return_points_won, return_games_won, break_points_converted
- **Other:** tie_break_record, deciding_set_record, retirement_record

### Phase 2.0 — Match Registry (source of truth)

```
flashscorefoundmatches          bettingsitefoundmatches
        │                               │
        └───────────────┬───────────────┘
                        ▼
          match by player1_name ↔ player2_name
          (both orderings checked)
                        │
                        ▼
          resolve player IDs from players table
                        │
                        ▼
          CREATE OR UPDATE tracked_matches
          (upsert by flashscore_match_id)
                        │
                        ▼
          return list[TrackedMatch]
```

**Matching rules:**
- Player names are already normalized (uppercase) — exact match only, no fuzzy matching
- Both `(fs.a, fs.b) == (bt.a, bt.b)` and `(fs.a, fs.b) == (bt.b, bt.a)` orderings are checked
- If multiple betting markets match → log error, skip match
- If no betting market matches → log warning, skip match
- Duplicate execution updates existing rows instead of inserting

### Phase 2.1 — Discovery Orchestrator (platform loop)

```
run_platform()
  │
  ├── discovery at startup
  │
  ├── while True:
  │     ├── update_match_statuses()   (DISCOVERED → LIVE, DB-only)
  │     ├── if time since last discovery >= DISCOVERY_INTERVAL_SECONDS:
  │     │     └── run_discovery_cycle()   (full scrape pipeline)
  │     └── sleep(STATUS_CHECK_INTERVAL_SECONDS)
  │
  └── set DISCOVERY_ENABLED=false to skip scheduled discovery
```

**Status Monitor — `update_match_statuses()`:**
- Reads `tracked_matches` where `tracking_enabled=true` and `status=DISCOVERED`
- If `scheduled_start` is not null: compares against `datetime.now(timezone.utc)`
- Naive datetimes are treated as UTC (SQLite strips timezone on `DateTime` without `timezone=True`)
- Transitions: **DISCOVERED → LIVE** only
- **FINISHED is NOT set here** — that is the responsibility of the live data scraper (Phase 2)

**Discovery — `run_discovery_cycle()`:**
- Runs once at startup, then every `DISCOVERY_INTERVAL_SECONDS` (default 12 h)
- Full scrape: Flashscore → Betting Site → new Players → Match Registry
- Every module wrapped in try/except

**Failure handling:**
- Status monitor tick failures are caught per tick
- Discovery failures are caught per cycle
- The platform never terminates

**Example log:**
```
Status: 3 transitioned to LIVE, 5 currently LIVE, 2 still DISCOVERED
=== Discovery cycle starting ===
Flashscore: 12 matches discovered, 8 new saved
...
Sleeping for 300 seconds...
```

**Error handling categories (all logged + continue):**
- Flashscore match with no betting market
- Betting market with no Flashscore match
- Missing player in players table
- Duplicate betting markets for one Flashscore match

### Phase 2.2 — Match Finalizer (research-ready summaries)

```
tracked_match (status=FINISHED)
         │
         ▼
  load live_scores + live_odds
         │
         ▼
  calculate stats (tick counts, gaps, timestamps, duplicates)
         │
         ▼
  validate (scores exist, odds exist, winner, duration, set score)
         │
         ▼
  determine winner from final set score
         │
         ▼
  INSERT completed_matches (always created — validation_passed reflects quality)
```

**Public API:**
- `finalize_match(session, tracked_match_id)` — finalize one match, returns `CompletedMatch`
- `run_match_finalizer(session)` — scan all FINISHED + not-yet-finalized, returns `list[CompletedMatch]`

**80% completeness rule:** `has_complete_score_data` when actual score ticks ≥ 0.8 × expected (duration / score_interval). Same for odds.

**Idempotent:** second call raises `AlreadyFinalized`. DB unique constraint on `tracked_match_id` prevents any duplicate row.

**Validation flags (set on every row, never blocks insertion):**
- `validation_passed` — scores exist, odds exist, duration > 0, winner determined, set scores not tied
- `has_complete_score_data` / `has_complete_odds_data` — 80% threshold
- `ready_for_replay` — both data types, gaps < 60s (scores) / 30s (odds)
- `ready_for_feature_extraction` — ≥10 score ticks
- `ready_for_backtesting` — both data types at 80%

---

## 4. Component Reference

### `config.py`
| Element | Type | Description |
|---------|------|-------------|
| `Settings` | `BaseSettings` | Pydantic model from `.env` |
| `settings.DATABASE_URL` | `str` | Default: `postgresql+psycopg2://...` |
| `settings.LOG_LEVEL` | `str` | Default: `"INFO"` |
| `settings.LOG_FORMAT` | `str` | Default: `"text"` |
| `settings` | instance | Global singleton |

### `database.py`
| Function/Class | Description |
|----------------|-------------|
| `engine` | SQLAlchemy Engine from `settings.DATABASE_URL` (PostgreSQL + psycopg2) |
| `SessionLocal` | `sessionmaker(bind=engine)` |
| `Base` | `DeclarativeBase` for ORM models |
| `get_db()` | Generator yielding Session, closes on exit |
| `check_connection()` | `SELECT 1` → bool |
| `init_db()` | Create all tables; convert `live_scores`/`live_odds` to hypertables (1d chunks); enable compression (7d); add reorder policy; idempotent via `IF NOT EXISTS` |

### `logger.py`
| Function | Description |
|----------|-------------|
| `setup_logging()` | Configures root logger to stdout with asctime/level/name/message format |

### `main.py`
| Function | Description |
|----------|-------------|
| `main()` | Setup logging, check DB, call `init_db()` then `run_platform()` |

### `orchestrator/service.py`
| Function | Description |
|----------|-------------|
| `run_platform()` | Main platform loop: startup discovery → status monitor forever |
| `update_match_statuses()` | DB-only: transitions DISCOVERED → LIVE based on UTC time comparison |
| `run_discovery_cycle()` | One-shot full scrape pipeline (FS → BT → TE → Registry) |
| `_count_by_status(status)` | Count tracked matches by status |
| `_update_missing_players(names)` | Query DB for existing players, send only missing ones to Tennis Explorer |

### `live_collector/flashscore_live.py`
| Function | Description |
|----------|-------------|
| `poll_flashscore_score()` | Fetch match page, parse live score state → `ScoreSnapshot` |
| `mark_match_finished(id)` | Set `tracked_matches.status=FINISHED`, calculate `match_duration_min` |
| `ScoreSnapshot` | Dataclass: set/game scores, point, server, tiebreak, finished, content_hash |

### `live_collector/betting_live.py`
| Function | Description |
|----------|-------------|
| `poll_betting_odds(market_id)` | POST odds endpoint, parse pipe string → `OddsSnapshot` |
| `OddsSnapshot` | Dataclass: back/lay odds, volume; any_valid(), content_hash |

### `live_collector/service.py`
| Function | Description |
|----------|-------------|
| `run_live_collection_loop()` | Background daemon: LIVE matches → asyncio.gather per match → batch INSERT |

### `finalizer/service.py`
| Function | Description |
|----------|-------------|
| `finalize_match(session, id)` | Finalize one FINISHED match → `CompletedMatch`. Raises `AlreadyFinalized` or `NotFinished`. |
| `run_match_finalizer(session)` | Scan all FINISHED + not-yet-finalized → `list[CompletedMatch]` |

### `finalizer/stats.py`
| Function | Description |
|----------|-------------|
| `calculate_stats(session, id)` | Load scores + odds, compute tick counts, gaps, duplicates, first/last timestamps → `MatchStats` |

### `finalizer/validation.py`
| Function | Description |
|----------|-------------|
| `validate(tm, stats, last_set_a, last_set_b)` | Check 80% completeness, winner, duration, set scores → `ValidationResult` with readiness flags |
| Function | Description |
|----------|-------------|
| `build_match_registry()` | Join flashscorefoundmatches ↔ bettingsitefoundmatches by player names, resolve player IDs, upsert tracked_matches, return list[TrackedMatch] |

### `collector/flashscore/client.py`
| Function | Description |
|----------|-------------|
| `fetch_mobile_listing()` | GET flashscore.mobi → HTML |
| `fetch_match_details(match_id)` | GET desktop match page → HTML |
| `fetch_match_details_batch(ids)` | async batch (8 concurrent) → dict of `{id: html}` |

### `collector/flashscore/parser.py`
| Function/Class | Description |
|----------------|-------------|
| `RawMatch` | Raw parsed listing data |
| `Match` | Enriched match with full names + parsed time |
| `parse_mobile_listing(html)` | BS4 parse → list of RawMatch |
| `filter_singles(matches)` | Filter to ATP/WTA/Challenger singles |
| `extract_full_names_from_title(html)` | Parse `<title>` → tuple `(player_a, player_b)` |
| `extract_match_date_from_title(html)` | Parse `<title>` → date |
| `build_match(raw, names, date)` | Combine → Match |

### `collector/flashscore/__init__.py`
| Function | Description |
|----------|-------------|
| `discover_matches()` | Full pipeline: fetch → parse → filter → enrich → return list[Match] |
| `save_matches_to_db(matches)` | Deduplicate by flashscore_match_id → INSERT, return count |

### `collector/betting_site/client.py`
| Function | Description |
|----------|-------------|
| `get_event_list()` | GET event list from API |
| `get_event_detail(event_id)` | POST event detail (runners, markets) |
| `get_market_odds(market_id)` | POST odds endpoint → pipe-delimited string or None |

### `collector/betting_site/parser.py`
| Function/Class | Description |
|----------------|-------------|
| `BettingsiteMatch` | Matched match + odds dataclass |
| `filter_tennis_matches(events)` | Filter by event_type_id=2 and " v " in name |
| `match_events_to_flashscore(events, fs_matches)` | Fuzzy match by last name → pairs |
| `parse_odds_pipe(data)` | Parse pipe string → `{selection_id: back_odds}` |
| `parse_odds_for_runners(data, a_id, b_id)` | Extract two runners' odds from pipe |

### `collector/betting_site/__init__.py`
| Function | Description |
|----------|-------------|
| `discover_matches(flashscore_matches)` | Full pipeline: list → filter → match → detail → odds → return list[BettingsiteMatch] |
| `save_matches_to_db(matches)` | Deduplicate by market_id → INSERT, return count |

### `collector/tennis_explorer/client.py`
| Function | Description |
|----------|-------------|
| `search_player(name)` | Search tennisexplorer.com → best matching player path |
| `fetch_player_profile(url_path)` | GET profile page → HTML |

### `collector/tennis_explorer/parser.py`
| Function/Class | Description |
|----------------|-------------|
| `PlayerData` | 45+ field comprehensive profile dataclass |
| `parse_player_profile(html, url)` | Parse full profile → PlayerData or None |

### `collector/tennis_explorer/__init__.py`
| Function | Description |
|----------|-------------|
| `update_player(name)` | Search → fetch → parse → upsert → bool |
| `update_players(names)` | Batch `update_player` per name → `{name: success}` |

---

## 5. Database Schema

### `flashscorefoundmatches`
| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK, autoincrement |
| flashscore_match_id | String(32) | UNIQUE, INDEXED |
| tournament | String(255) | |
| player_a | String(255) | |
| player_b | String(255) | |
| scheduled_start_time | DateTime | nullable |
| status | String(50) | |
| discovered_at | DateTime | default=utcnow |

### `bettingsitefoundmatches`
| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK, autoincrement |
| market_id | String(64) | UNIQUE, INDEXED |
| match_url | String(512) | |
| player_a | String(255) | |
| player_b | String(255) | |
| odds_player_a | Float | nullable |
| odds_player_b | Float | nullable |
| discovered_at | DateTime | default=utcnow |

### `players`
| Column | Type | Constraints |
|--------|------|-------------|
| player_id | Integer | PK, autoincrement |
| full_name | String(255) | UNIQUE, INDEXED |
| first_name, last_name | String(255) | nullable |
| nationality | String(100) | nullable |
| date_of_birth | String(20) | nullable |
| age, height, weight | Integer | nullable |
| plays | String(50) | nullable |
| backhand | String(50) | nullable |
| gender | String(10) | nullable |
| atp_or_wta | String(10) | nullable |
| profile_url | String(512) | nullable |
| current_rank, career_high_rank, ranking_points | Integer | nullable |
| total_matches, total_wins, total_losses | Integer | nullable |
| career_win_percentage | Float | nullable |
| *Surface stats (clay/hard/grass/indoor)* | | |
| `{surface}_matches/wins/losses` | Integer | nullable |
| `{surface}_win_percentage` | Float | nullable |
| *Serve/return stats* | Float | nullable |
| tie_break_record, deciding_set_record, retirement_record | String(32) | nullable |
| source | String(64) | default="Tennis Explorer" |
| created_at | DateTime | |
| last_updated | DateTime | |

**No foreign key relationships between `flashscorefoundmatches`, `bettingsitefoundmatches`, and `players`** — matches are linked at the application layer via the matching logic in `parser.py` and `registry/service.py`.

### `tracked_matches`
| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK, autoincrement |
| flashscore_match_id | String(32) | UNIQUE, INDEXED |
| betting_market_id | String(64) | UNIQUE, INDEXED, nullable |
| player1_id | Integer | nullable (FK to players) |
| player2_id | Integer | nullable (FK to players) |
| player1_name | String(255) | |
| player2_name | String(255) | |
| tournament | String(255) | |
| round | String(100) | nullable |
| surface | String(50) | nullable |
| scheduled_start | TIMESTAMPTZ | nullable |
| actual_finish | TIMESTAMPTZ | nullable — set by live collector |
| match_duration_min | Integer | nullable — calculated on finish |
| live_url | String(512) | nullable — Flashscore match page URL |
| status | String(50) | default=`DISCOVERED` |
| tracking_enabled | Boolean | default=True |
| created_at | TIMESTAMPTZ | default=utcnow |
| updated_at | TIMESTAMPTZ | auto-updates on change |

### `live_scores` (hypertable)
| Column | Type | Constraints |
|--------|------|-------------|
| id | BigInt | PK |
| tracked_match_id | Integer | INDEXED, NOT NULL |
| flashscore_match_id | String(32) | NOT NULL |
| timestamp | TIMESTAMPTZ | NOT NULL, partition key |
| set_score_a/b | Smallint | nullable |
| game_score_a/b | Smallint | nullable |
| point_score | String(8) | nullable |
| server | String(255) | nullable |
| is_tiebreak | Boolean | default=False |
| match_finished | Boolean | default=False |
| content_hash | String(64) | NOT NULL |
| | `UNIQUE(tracked_match_id, timestamp, content_hash)` |

### `live_odds` (hypertable)
| Column | Type | Constraints |
|--------|------|-------------|
| id | BigInt | PK |
| tracked_match_id | Integer | INDEXED, NOT NULL |
| betting_market_id | String(64) | NOT NULL |
| timestamp | TIMESTAMPTZ | NOT NULL, partition key |
| back_odds_a/b | Float | nullable |
| lay_odds_a/b | Float | nullable |
| volume_a/b | Float | nullable |
| content_hash | String(64) | NOT NULL |
| | `UNIQUE(tracked_match_id, timestamp, content_hash)` |

### `completed_matches`
| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK, autoincrement |
| tracked_match_id | Integer | UNIQUE, INDEXED |
| flashscore_match_id | String(32) | |
| betting_market_id | String(64) | nullable |
| player1_id, player2_id | Integer | nullable |
| tournament | String(255) | |
| round | String(100) | nullable |
| surface | String(50) | nullable |
| scheduled_start | TIMESTAMPTZ | nullable |
| actual_finish | TIMESTAMPTZ | nullable |
| duration_minutes | Integer | nullable |
| winner_player_id | Integer | nullable |
| final_set_score | String(20) | e.g. `"2-1"` |
| total_sets | Integer | nullable |
| score_tick_count | Integer | |
| odds_tick_count | Integer | |
| first/last_score_timestamp | TIMESTAMPTZ | nullable |
| first/last_odds_timestamp | TIMESTAMPTZ | nullable |
| score/odds_collection_duration_seconds | Integer | nullable |
| duplicate_score/odds_ticks | Integer | |
| largest_score/odds_gap_seconds | Float | nullable |
| has_complete_score_data | Boolean | 80% threshold |
| has_complete_odds_data | Boolean | 80% threshold |
| ready_for_replay | Boolean | |
| ready_for_feature_extraction | Boolean | |
| ready_for_backtesting | Boolean | |
| validation_passed | Boolean | all critical checks |
| exported | Boolean | default=False |
| finalized_at | TIMESTAMPTZ | |
| collector_version | String(32) | default=`"3.0.0"` |

---



## 6. Future Modules (Stubbed)

| Module | Phase | Purpose |
|--------|-------|---------|
| `collector/` | Phase 0 ✅ | Data collection from Flashscore, Betting Site, Tennis Explorer |
| `registry/` | Phase 2.0 ✅ | Match Registry — canonical match records |
| `orchestrator/` | Phase 2.1 ✅ | Platform loop — status monitor + scheduled discovery |
| `live_collector/` | Phase 2 ✅ | Live score & odds collection — TimescaleDB hypertables |
| `finalizer/` | Phase 2.2 ✅ | Match Finalizer — `completed_matches` table, stats, validation |
| `storage/` | Phase 3 | Append-only tick storage for live data |
| `replay/` | Phase 3 | Replay any recorded match exactly as it happened |
| `research/` | Phase 5 | Research notebooks, probability calculations |
| `backtest/` | Phase 6 | Backtesting engine for strategies |
| `models/` | Phase 7 | ML models for probability estimation |
| `execution/` | Phase 9 | Live trade execution |
| `dashboard/` | Phase 10 | Monitoring dashboard |

---

## 7. Configuration

**File:** `.env` (see `.env.example`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+psycopg2://...` | PostgreSQL/TimescaleDB connection |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | `text` | Log output format |
| `STATUS_CHECK_INTERVAL_SECONDS` | `300` | Status-monitor poll interval (5 min) |
| `DISCOVERY_INTERVAL_SECONDS` | `43200` | Discovery cycle interval (12 h) |
| `DISCOVERY_ENABLED` | `True` | Enable scheduled discovery |
| `LIVE_SCORE_INTERVAL_SECONDS` | `10` | Score poll interval |
| `LIVE_ODDS_INTERVAL_SECONDS` | `2` | Odds poll interval |
| `LIVE_PREFETCH_MINUTES` | `5` | Pre-fetch URL before start |

---

## 8. Testing

**Framework:** pytest

**Test files:**

| File | Tests |
|------|-------|
| `tests/test_config.py` | Settings defaults |
| `tests/test_database.py` | Connection check |
| `tests/test_flashscore_collector.py` | 28 tests across 7 classes |
| `tests/test_bettingsite_collector.py` | 36 tests across 7 classes |
| `tests/test_tennis_explorer_collector.py` | 34 tests across 7 classes |
| `tests/test_match_registry.py` | 10 tests across 1 class |
| `tests/test_orchestrator.py` | 16 tests across 3 classes |
| `tests/test_live_collector.py` | 13 tests across 4 classes |
| `tests/test_match_finalizer.py` | 19 tests across 7 classes |

**Key patterns:**
- Unit tests with sample HTML strings (no network calls)
- Integration tests with mocked `httpx` clients
- Database integration tests (insert, verify, cleanup teardown)

---

## 9. Development Workflow

Per the roadmap, each phase must satisfy its Definition of Done before moving forward:

1. Define requirements
2. Review architecture
3. Generate implementation prompt
4. Implement with coding agent
5. Review implementation
6. Fix issues
7. Mark phase complete
8. Move to next phase

**Never implement multiple phases simultaneously.**
