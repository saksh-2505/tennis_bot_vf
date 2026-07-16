# Sports Trading Platform V3 — Architecture

**Working directory:** `sports-trading/` (inside `/home/matrix/Desktop/brain/tennis_bot_vf/`)

## 1. Project Overview

Live tennis data collection, replay, research, backtesting, and execution platform.

**Stack:** Python >=3.12, SQLAlchemy 2.x, httpx, BeautifulSoup4, Pydantic Settings, TimescaleDB (PostgreSQL 16)

**Current Status:** 152 Python files, 16,110 lines (excl. tests/). Updated 2026-07-16 17:46 UTC.

**Auto-generated file stats:** 152 Python files, 16,110 lines (excl. tests/). Updated 2026-07-16 17:46 UTC.

- **incidents/**: 16 files, 2,614 lines
- **verification/**: 26 files, 2,232 lines
- **observability/**: 18 files, 1,980 lines
- **console_api/**: 24 files, 1,964 lines
- **collector/**: 10 files, 1,303 lines
- **live_collector/**: 5 files, 1,155 lines
- **matcher/**: 4 files, 838 lines
- **repair/**: 4 files, 641 lines
- **scripts/**: 8 files, 563 lines
- **finalizer/**: 5 files, 524 lines
- **models/**: 10 files, 469 lines
- **orchestrator/**: 2 files, 427 lines
- **reports/**: 2 files, 389 lines
- **root/**: 6 files, 361 lines
- **monitor/**: 1 files, 291 lines
- **registry/**: 2 files, 177 lines
- **shared/**: 3 files, 152 lines
- **backtest/**: 1 files, 5 lines
- **dashboard/**: 1 files, 5 lines
- **execution/**: 1 files, 5 lines
- **replay/**: 1 files, 5 lines
- **research/**: 1 files, 5 lines
- **storage/**: 1 files, 5 lines
---

## All Fixes (2026-07-06 → 2026-07-10)

| Date | Fix | Files | Impact |
|------|-----|-------|--------|
| Jul 10 | `_word_matches` short-name false positives | `collector/betting_site/parser.py` | Words <4 chars now require word-boundary match (`" ma " in " event "`) instead of substring match (`"ma" in "maxime"`). Prevents "MA L.", "WU Y.", etc. from matching 3+ betting markets and crashing registry. |
| Jul 10 | Registry: IntegrityError crash guard | `registry/service.py` | Before assigning `betting_market_id`, checks another TrackedMatch doesn't already have it. Skips instead of aborting entire `build_match_registry()` cycle. |
| Jul 10 | Registry: set `actual_finish` on FINISHED | `registry/service.py` | When registry transitions a match to FINISHED/RETIRED/WALKOVER, records `actual_finish` timestamp. |
| Jul 10 | DB: backfill `actual_finish` | Oracle VM | 81 FINISHED matches without `actual_finish` backfilled with `updated_at`. |
| Jul 8 | Name matching: abbreviated Flashscore names | `collector/betting_site/parser.py` | `_extract_last_name` now handles "LAST INITIAL" format (e.g. "DJOKOVIC N" → "djokovic" not "n"). |
| Jul 8 | Registry: last-name matching | `registry/service.py` | `build_match_registry()` uses `_names_match` instead of exact tuple matching. |
| Jul 8 | Odds interval 2s → 3s | `config.py`, `.env.example`, `docker-compose.yml` | Per user request |
| Jul 7 | Retention policy | `database.py` | 90-day hypertable retention for `live_scores`, `live_odds`, `system_events`. |
| Jul 7 | Stuck DISCOVERED matches | `orchestrator/service.py` | Matches with `scheduled_start=NULL` expire after 24h → EXPIRED. |
| Jul 7 | `_parse_time()` timezone fix | `collector/flashscore/parser.py` | Now returns timezone-aware UTC (was naive local time). |
| Jul 7 | Dict cleanup on match finish | `live_collector/service.py` | `_score_hash`, `_odds_hash`, `_score_last_poll` pruned when match finishes. |
| Jul 7 | Unused parameter removal | `live_collector/flashscore_live.py` | `match_id: str` → `tracked_match_id: int` in `poll_flashscore_score`. |
| Jul 6 | Odds API headers + parser reuse | `live_collector/betting_live.py` | Origin/Referer headers matching discovery client. Pipe parsing uses battle-tested `parse_odds_pipe`. |
| Jul 6 | Multi-format player name resolution | `registry/service.py` | `_find_player()` tries exact, reversed, last-name partial, abbreviated names. |
| Jul 6 | Match duration calculation | `live_collector/flashscore_live.py` | Falls back to first score tick when `scheduled_start` is after `actual_finish` or >8h. |
| Jul 6 | Lazy betting market matching | `live_collector/service.py` | Every 60s, re-attempts fuzzy name matching for LIVE matches without a betting market. |
| Earlier | SQLAlchemy `text()` fix | `incidents/recovery.py` | Params passed to `execute()` instead of `text()`. |
| Earlier | Monitor healthcheck | `Dockerfile.monitor` | Added `procps` for `pgrep`. |
| Earlier | Observability wiring | `main.py`, `run_monitor.py` | `initialize_observability()` + JSON structured logging. |
| Earlier | Telegram consolidation | `shared/notify.py` | All 4 Telegram callers delegate to single client. |

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

┌─────────────────────────────────────────────────────────────────────┐
│  CRON (every 5 min) — tennis_bot_monitor.py                         │
│  ├── Container health — Telegram alerts (down/recovery)             │
│  ├── Error digest — new WARNING/ERROR in app logs → Telegram        │
│  ├── Daily report — match/tick counts → Telegram                    │
│  └── DuckDNS update                                                 │
└────────────────────────────────────────────────────────────────────┘

                         ▼
┌───────────────────────────────────────────────────────────────────────┐
│  INCIDENT MANAGER — run_monitor.py (Docker, restart: always)          │
│  ∞ loop (60s interval):                                                │
│  ├── CPU/RAM/Disk thresholds                                          │
│  ├── DB connectivity                                                  │
│  ├── 6 collector health checks (staleness via DB timestamps)          │
│  ├── Live match health (score/odds freshness)                         │
│  ├── Unfinalized finished match detection                             │
│  ├── create_incident() — dedup by SHA-256 hash                        │
│  ├── generate_incident_package() — JSON, logs, metrics, config, source│
│  ├── send_notification() — Telegram CRITICAL alerts                   │
│  ├── attempt_recovery() — safe DB retry                               │
│  └── auto-resolve when condition clears                               │
└───────────────────────────────────────────────────────────────────────┘

                         ▼
┌────────────────────────────────────────────────────────────────────┐
│                        TIMESCALEDB (PostgreSQL 16)                  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  Regular tables: flashscorefoundmatches, bettingsitefoundmatches│
│  │  players, tracked_matches, completed_matches, incidents       │ │
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
│  │  players, tracked_matches, incidents                     │  │
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
- Player names are normalized (uppercase) — multi-format resolution via `_find_player()` (see below)
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
| `Settings` | `BaseSettings` | Pydantic model from `.env`, `extra="ignore"` (allows unknown env vars) |
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
| `init_db()` | Create all tables via `metadata.create_all`; convert `live_scores`/`live_odds` to hypertables (1d chunks via `create_hypertable`); enable per-table compression with `segmentby=tracked_match_id` (via `ALTER TABLE ... SET`); add compression policy (7d interval) and reorder policy with graceful try/except fallback; idempotent via `if_not_exists` guards |

### `logger.py`
| Function | Description |
|----------|-------------|
| `setup_logging()` | Configures root logger to stdout with asctime/level/name/message format |

### `main.py`
| Function | Description |
|----------|-------------|
| `main()` | Initialize observability, setup JSON structured logging, check DB, init DB, run platform |

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
| `mark_match_finished(id)` | Set `tracked_matches.status=FINISHED`, calculate `match_duration_min`. Uses `scheduled_start` by default; falls back to `min(live_scores.timestamp)` if scheduled_start is in the future or >8h before finish. |
| `ScoreSnapshot` | Dataclass: set/game scores, point, server, tiebreak, finished, content_hash |

### `live_collector/betting_live.py`
| Function | Description |
|----------|-------------|
| `poll_betting_odds(market_id)` | POST odds endpoint with Origin/Referer headers, parse pipe string via shared `parse_odds_pipe` from collector → `OddsSnapshot` |
| `OddsSnapshot` | Dataclass: back/lay odds, volume; any_valid() (back odds only), content_hash |
| `_parse_odds_response(body, market_id)` | JSON array → extract pipe → delegate to `_parse_odds_pipe_snapshot` |
| `_parse_odds_pipe_snapshot(pipe, market_id)` | Reuses `collector.betting_site.parser.parse_odds_pipe` for robust pipe parsing |

### `live_collector/service.py`
| Function | Description |
|----------|-------------|
| `run_live_collection_loop()` | Background daemon: LIVE matches → asyncio.gather per match → batch INSERT (scores every 10s, odds every 2s, hash-deduplicated) |
| `_collect_tick(matches)` | Concurrent polling: scores (10s throttle) + odds (every tick), both only inserted on hash change |
| `_get_live_matches()` | Fetch LIVE + upcoming matches; pre-fetch URLs; run lazy betting market matching |
| `_try_lazy_betting_match(session, matches)` | Every 60s, attempt to find betting markets for LIVE matches without one (fuzzy last-name match against bettingsitefoundmatches) |

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
| `build_match_registry()` | Join flashscorefoundmatches ↔ bettingsitefoundmatches by player names, resolve player IDs via `_find_player()`, upsert tracked_matches, return list[TrackedMatch] |
| `_find_player(session, name)` | Multi-format player lookup: exact match → reversed (LAST FIRST) → last-name partial. Handles abbreviated names (initials) by skipping short final tokens. |

### `monitor/tennis_bot_monitor.py`
| Function | Description |
|----------|-------------|
| `run()` | Main entry: DuckDNS update → container health check → down/recovery alerts → error digest → daily report |
| `check_containers()` | `docker compose ps --format json` → `(app_ok, db_ok, err_msg)` |
| `get_recent_logs(since_seconds)` | Fetch recent app container logs |
| `extract_errors(log_text)` | Filter lines containing ERROR/exception/traceback |
| `get_db_stats()` | Query TimescaleDB for match counts, tick counts via `docker compose exec` |
| `update_duckdns()` | GET `duckdns.org/update?domains=...&token=...&ip=...` |
| `send_telegram(text)` | POST message to Telegram bot API |
| `load_state()` / `save_state(state)` | Persist health state to `state.json` for transition detection |

### `incidents/models.py`
| Element | Type | Description |
|---------|------|-------------|
| `Incident` | `Base` ORM | 16-column table, self-creating (ad-hoc like `players`) |
| `incident_hash` | String(64) | SHA-256 for dedup, indexed (not unique — allows recurrence) |

### `incidents/service.py`
| Function | Description |
|----------|-------------|
| `create_incident(session, ...)` | Hash → insert OR update if OPEN/ACKNOWLEDGED/RECOVERING |
| `resolve_incident(session, id)` | Set status=RESOLVED, resolved_at=now |
| `acknowledge_incident(session, id)` | Set status=ACKNOWLEDGED |
| `get_open_incidents(session)` | Query OPEN + ACKNOWLEDGED + RECOVERING |
| `list_by_module(session, module)` | Filter by module, newest first |
| `_compute_hash(category, module, title)` | SHA-256 for deterministic dedup |

### `incidents/monitor.py`
| Function | Description |
|----------|-------------|
| `monitor_platform()` | Infinite loop: check everything → create incidents → notify → recover → auto-resolve |
| `_run_tick(session)` | One monitoring cycle — all checks |
| `_check_cpu()` / `_check_memory()` / `_check_disk()` | Infrastructure thresholds (configurable %) |
| `_check_database(session)` | `SELECT 1` → CRITICAL if unreachable |
| `_check_collectors(session)` | 4 collectors: MAX(timestamp) staleness check |
| `_check_live_collector(session)` | Live collector: MAX(live_scores.timestamp) staleness |
| `_check_finalizer(session)` | Finalizer: MAX(completed_matches.finalized_at) staleness |
| `_check_live_matches(session)` | Per LIVE match: score/odds freshness |
| `_check_unfinalized_finished(session)` | FINISHED matches without completed_matches row |
| `_auto_resolve_healed(session, currents)` | Resolve incidents whose condition is no longer detected |
| `_to_timestamp(val)` | Normalize datetime/string/float → Unix timestamp |

### `incidents/package_generator.py`
| Function | Description |
|----------|-------------|
| `generate_incident_package(session, incident)` | Create full diagnostic package directory |
| `_write_incident_json(path, incident)` | Core incident record as JSON |
| `_collect_logs(path, incident)` | Try `docker compose logs --tail 500` for app logs |
| `_collect_metrics(path)` | CPU/RAM/Disk via os + shutil |
| `_collect_environment(path)` | Python version, OS, pip freeze, DB version |
| `_collect_system_state(path, session)` | Active matches, tick counts, open incidents |
| `_collect_configuration(path)` | Sanitized `.env` (redact tokens/passwords/keys) |
| `_collect_architecture(path)` | architecture.md path + git commit hash |
| `_collect_source(path, incident)` | Copy affected module source files |
| `_sanitize_value(key, value)` | Replace secrets with `<REDACTED>` |

### `incidents/notifier.py`
| Function | Description |
|----------|-------------|
| `send_notification(incident)` | POST CRITICAL alert to Telegram (no stack traces) |
| `_format_incident_alert(incident)` | Severity icon + module + title + summary + ID |

### `incidents/recovery.py`
| Function | Description |
|----------|-------------|
| `attempt_recovery(session, incident)` | Safe recovery: DB retry, collector retry, live match forced poll |
| `_retry_db_connection(incident)` | `SELECT 1` via SQLAlchemy engine |
| `_retry_collector(session, incident)` | Probe live Flashscore endpoint for stalled collectors |
| `_retry_live_match(session, incident)` | Forced Flashscore poll + odds poll for stale matches |

### `incidents/telegram_bot.py`
| Function | Description |
|----------|-------------|
| `check_commands(session)` | Poll Telegram `getUpdates`, dispatch commands, reply |
| `_handle_command(session, text)` | Route `/status`, `/matches`, `/match <id>`, `/scores`, `/odds`, `/incidents` |
| `_status(session)` | DB health, live match count, tick counts, open incidents |
| `_matches(session)` | Match counts by status, list of LIVE matches |
| `_match_detail(session, id)` | Full match row + score/odds stats + finalized status |
| `_scores(session)` | For each LIVE match: set/game scores, point, tiebreak |
| `_odds(session)` | For each LIVE match: back odds for both players |
| `_incidents(session)` | Open incidents with severity, category, occurrence count |
| `_send_reply(chat_id, text)` | POST HTML response back to Telegram |
| `_fetch_updates(offset)` | GET pending updates since last offset |
| `_read_offset()` / `_write_offset()` | Persist update offset to `/tmp/telegram_offset` |

Called once per monitor tick (60s) from `_run_tick()`.

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
| tracked_match_id | Integer | PK (composite), NOT NULL |
| timestamp | TIMESTAMPTZ | PK (composite), partition key |
| content_hash | String(64) | PK (composite), NOT NULL |
| flashscore_match_id | String(32) | NOT NULL |
| set_score_a/b | Integer | nullable |
| game_score_a/b | Integer | nullable |
| point_score | String(8) | nullable |
| server | String(255) | nullable |
| is_tiebreak | Boolean | default=False |
| match_finished | Boolean | default=False |

### `live_odds` (hypertable)
| Column | Type | Constraints |
|--------|------|-------------|
| tracked_match_id | Integer | PK (composite), NOT NULL |
| timestamp | TIMESTAMPTZ | PK (composite), partition key |
| content_hash | String(64) | PK (composite), NOT NULL |
| betting_market_id | String(64) | NOT NULL |
| back_odds_a/b | Float | nullable |
| lay_odds_a/b | Float | nullable |
| volume_a/b | Float | nullable |

### `system_events` (hypertable)

| Column | Type | Constraints |
|--------|------|-------------|
| timestamp | TIMESTAMPTZ | PK (composite), partition key |
| event_id | String(32) | PK (composite), auto-generated |
| level | String(16) | INFO, WARNING, ERROR, CRITICAL |
| source | String(64) | Module/service that generated the event |
| message | Text | Event description |
| details | Text | nullable — JSON blob with structured context |
| incident_id | Integer | nullable — FK to incidents |
| tracked_match_id | Integer | nullable — FK to tracked_matches |

Hypertable with 1-day chunk interval, compression enabled (7-day policy).

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

### `incidents`

| Column | Type | Constraints |
|--------|------|-------------|
| incident_id | Integer | PK, autoincrement |
| severity | String(16) | INFO, WARNING, ERROR, CRITICAL |
| status | String(16) | OPEN, ACKNOWLEDGED, RECOVERING, RESOLVED, CLOSED |
| category | String(32) | Collector Failure, Database, Network, Infrastructure, Data Validation, Match Collection, Unknown |
| module | String(64) | Affected module |
| tracked_match_id | Integer | nullable |
| collector_name | String(64) | nullable |
| title | String(256) | Short summary |
| summary | Text | Full description |
| incident_hash | String(64) | INDEXED, SHA-256 dedup key |
| first_detected_at | TIMESTAMPTZ | |
| last_detected_at | TIMESTAMPTZ | Auto-updates on dedup |
| resolved_at | TIMESTAMPTZ | nullable |
| occurrence_count | Integer | Incremented on dedup |
| recovery_attempts | Integer | Incremented on recovery |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | Auto-updates |

---

|---



## 6. Future Modules (Stubbed)

| Module | Phase | Purpose |
|--------|-------|---------|
| `collector/` | Phase 0 ✅ | Data collection from Flashscore, Betting Site, Tennis Explorer |
| `registry/` | Phase 2.0 ✅ | Match Registry — canonical match records |
| `orchestrator/` | Phase 2.1 ✅ | Platform loop — status monitor + scheduled discovery |
| `live_collector/` | Phase 2 ✅ | Live score & odds collection — TimescaleDB hypertables |
| `finalizer/` | Phase 2.2 ✅ | Match Finalizer — `completed_matches` table, stats, validation |
| `monitor/` | Phase 2.3 ✅ | Health checks, Telegram alerts, error digests, daily reports, DuckDNS |
| `incidents/` | Phase 3.1 ✅ | Incident Manager — continuous monitoring, dedup, diagnostic packages, safe recovery |
| `storage/` | Phase 3 | Append-only tick storage for live data |
| `replay/` | Phase 3 | Replay any recorded match exactly as it happened |
| `research/` | Phase 5 | Research notebooks, probability calculations |
| `backtest/` | Phase 6 | Backtesting engine for strategies |
| `models/` | Phase 7 | ML models for probability estimation |
| `execution/` | Phase 9 | Live trade execution |
| `dashboard/` | Phase 10 | Web monitoring dashboard (empty stub) |

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
| `TELEGRAM_BOT_TOKEN` | (secret) | Bot token for health alerts |
| `TELEGRAM_CHAT_ID` | (secret) | Destination chat for alerts |
| `INCIDENT_MONITOR_INTERVAL` | `60` | Incident check cycle (seconds) |
| `INCIDENT_SCORE_STALE` | `120` | Score staleness threshold (seconds) |
| `INCIDENT_ODDS_STALE` | `60` | Odds staleness threshold (seconds) |
| `INCIDENT_COLLECTOR_STALE` | `7200` | Collector staleness threshold (seconds) |
| `INCIDENT_UNFINALIZED_STALE` | `1800` | Unfinalized match threshold (seconds) |
| `INCIDENT_CPU_THRESHOLD` | `90` | CPU alert threshold (%) |
| `INCIDENT_MEMORY_THRESHOLD` | `90` | Memory alert threshold (%) |
| `INCIDENT_DISK_THRESHOLD` | `90` | Disk alert threshold (%) |
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

## 9. Deployment

**Platform:** Oracle Cloud Always Free (ARM Ampere A1, 4 OCPU, 15 GB RAM, 49 GB boot disk)

### Stack
```
Oracle VM (Ubuntu 22.04, x86_64)
│
├── Docker Compose
│   ├── timescaledb (timescale/timescaledb:latest-pg16)
│   │   └── pgdata volume  (persistent)
│   │   └── healthcheck: pg_isready
│   │
│   ├── app (python:3.12-slim, built on VM)
│   │   ├── main.py — orchestrator + live collector
│   │   └── env vars via docker-compose.yml
│   │
│   └── monitor (python:3.12-slim, Dockerfile.monitor)
│       ├── run_monitor.py — incident management loop
│       ├── └── env vars: DATABASE_URL, TELEGRAM_*, INCIDENT_*
│       └── incident_packages volume (persistent) environment:
│           DATABASE_URL, LOG_LEVEL, LOG_FORMAT,
│           DISCOVERY_*, LIVE_*, TELEGRAM_*
│
├── Cron (every 5 min)
│   ├── monitor/tennis_bot_monitor.py
│   │   ├── DuckDNS update
│   │   ├── container health → Telegram alert
│   │   ├── error digest → Telegram
│   │   └── daily report → Telegram
│   └── curl DuckDNS fallback
│
├── Logrotate (30-day retention, 100 MB max per file)
│   └── /home/ubuntu/tennis_bot/logs/*.log
│
├── Docker restart policy (restart: always on all services)
│   └── Systemd tennis-bot.service defined but inactive
│
├── Healthchecks
│   ├── timescaledb: pg_isready (10s interval)
│   ├── app: DB connectivity check (30s interval)
│   └── monitor: process check via pgrep (30s interval)
│
├── Shared volumes
│   ├── pgdata: persistent TimescaleDB data
│   ├── incident_packages: diagnostic packages from monitor
│   └── shared_logs: mounted at /app/logs on app + monitor for log access
│
└── DuckDNS: tennisbotdata.duckdns.org → 161.118.182.103
```

### Infrastructure
| Service | Purpose |
|---------|---------|
| DuckDNS | Free dynamic DNS — `tennisbotdata.duckdns.org` |
| Telegram bot | Downtime alerts + error digests + daily reports |
| Docker `restart: always` | Container restart on crash |
| Logrotate | Prevents disk exhaustion |
| GitHub | Source of truth — `saksh-2505/tennis_bot_vf` |

### Key environment variables
| Variable | Set by | Purpose |
|----------|--------|---------|
| `DATABASE_URL` | docker-compose.yml | Points to `timescaledb:5432` |
| `DB_PASSWORD` | `.env` file | Superuser password for PostgreSQL |
| `TELEGRAM_BOT_TOKEN` | `.env` file (all services) | Bot token for health alerts |
| `TELEGRAM_CHAT_ID` | `.env` file (all services) | Destination chat for alerts |

> **Note:** All services read credentials from environment variables. No hardcoded tokens remain in any source file. All Telegram outbound calls are consolidated through `shared/notify.py`.

### `docker-compose.yml` structure
```
services:
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_USER: tennis
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: tennis_bot
    volumes: pgdata:/var/lib/postgresql/data
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tennis"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build: .
    depends_on:
      timescaledb:
        condition: service_healthy
    environment:
      DATABASE_URL: "postgresql+psycopg2://tennis:${DB_PASSWORD}@timescaledb:5432/tennis_bot"
      LOG_LEVEL: "INFO"
      LOG_FORMAT: "text"
      DISCOVERY_ENABLED: "true"
      DISCOVERY_INTERVAL_SECONDS: "43200"
      STATUS_CHECK_INTERVAL_SECONDS: "300"
      LIVE_SCORE_INTERVAL_SECONDS: "10"
      LIVE_ODDS_INTERVAL_SECONDS: "2"
      LIVE_PREFETCH_MINUTES: "5"
      TELEGRAM_BOT_TOKEN: "${TELEGRAM_BOT_TOKEN}"
      TELEGRAM_CHAT_ID: "${TELEGRAM_CHAT_ID}"
    volumes:
      - shared_logs:/app/logs
    restart: always
    healthcheck:
      test: ["CMD", "python", "-c", "from database import check_connection; exit(0) if check_connection() else exit(1)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
```

### `Dockerfile` structure
```
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
        pydantic-settings sqlalchemy psycopg2-binary httpx beautifulsoup4 pytest
COPY . .
CMD ["python", "main.py"]
```

### Production-specific model constraints
- `live_scores` and `live_odds` use **composite primary keys** `(tracked_match_id, timestamp, content_hash)` instead of auto-increment `id` — required by TimescaleDB (partition column must be part of every PK/unique index)
- `init_db()` enables compression via `ALTER TABLE ... SET (timescaledb.compress)` before adding `add_compression_policy` — incorrect order causes `columnstore not enabled` error
- `Settings` model uses `extra="ignore"` to silently accept non-application env vars (`DB_PASSWORD`, `TELEGRAM_*`)

### Update workflow
1. Push changes to `saksh-2505/tennis_bot_vf`
2. SSH: `cd ~/tennis_bot && git pull`
3. `docker compose build app monitor && docker compose up -d`

---

## 10. Development Workflow

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

---

## 11. Repository Structure (Post-Transformation)

```
sports-trading/
├── main.py                     # Platform entry point
├── config.py                   # Pydantic settings
├── database.py                 # SQLAlchemy engine + SessionLocal
├── logger.py                   # Logging configuration
├── run_monitor.py              # Incident monitor entry
├── CONTRIBUTING.md             # Engineering standards
│
├── shared/                     # Reusable utilities
│   ├── httpx_client.py         # Centralized HTTP client
│   ├── notify.py               # Centralized Telegram sender (all callers consolidated)
│   └── event_logger.py         # Structured event logger → system_events hypertable
│
├── collector/                  # Data collectors
│   ├── flashscore/
│   ├── betting_site/
│   └── tennis_explorer/
│
├── models/                     # ORM models
├── orchestrator/service.py     # Main platform loop
├── registry/service.py         # Match registry
├── finalizer/                  # Match finalization
├── live_collector/             # Live data polling
│
├── incidents/
│   ├── telegram_bot/           # Split into 7 files
│   │   ├── __init__.py
│   │   ├── router.py           # polling, routing, offset
│   │   ├── helpers.py          # send_reply, HTML escaping
│   │   ├── offset_store.py     # offset file persistence
│   │   ├── handlers_match.py   # /matches, /match, /today etc.
│   │   ├── handlers_live.py    # /scores, /odds, history
│   │   ├── handlers_player.py  # /players, /player
│   │   └── handlers_system.py  # /status, /incidents, /db_stats
│   └── ... (monitor, service, models, config, recovery, etc.)
│
├── monitor/tennis_bot_monitor.py  # Credentials now from env vars
├── tests/
├── docs/                       # Centralized documentation
│   ├── architecture.md         #   this file
│   ├── database.md             #   schema, hypertables, indexes
│   ├── code_index.md           #   every module with API + deps
│   ├── project_state.md        #   completed work, blockers, roadmap
│   └── adr/                    #   10 Architecture Decision Records
├── scripts/                    # AI Context Engine
│   ├── generate_feature_context.py
│   ├── generate_incident_package.py
│   ├── update_code_index.py
│   ├── dependency_graph.py
│   └── validate_module_boundaries.py
└── .ai/                        # AI development config
    ├── RULES.md                # AI coding rules
    ├── context_config.yaml     # per-module load recommendations
    └── agent_definitions.yaml  # specialized agent team
```

## 12. AI Workflow

Every AI session loads:
1. `.ai/RULES.md` — coding rules
2. `docs/code_index.md` — module overview
3. `docs/database.md` — schema reference
4. Relevant module files via `scripts/generate_feature_context.py`

For bugs:
1. `scripts/generate_incident_package.py` — collect logs + diff
2. Read related module documentation
3. Read relevant test files
4. Fix and verify

## 13. Module Boundary Rules

| Module | May Import | May NOT Import |
|--------|-----------|----------------|
| `collector/*` | `models`, `shared`, `database` | `orchestrator`, `incidents`, `finalizer`, `matcher`, `repair` |
| `matcher/*` | `database` (for models) | `collector`, `orchestrator`, `finalizer`, `live_collector` |
| `repair/*` | `models`, `finalizer` | `collector`, `orchestrator`, `live_collector` |
| `reports/*` | `models` | `collector`, `matcher`, `repair` |
| `registry` | `models`, `matcher`, `database` | `incidents`, `finalizer` |
| `orchestrator` | Everything | `incidents` |
| `finalizer` | `models` | `collector`, `incidents` |
| `live_collector` | `models`, `matcher`, `config` | `incidents`, `registry` |
| `incidents` | `database` | `orchestrator`, `collector` |
| `shared` | Nothing internal | Everything else |
| `verification/*` | `models`, `database`, `shared` | `collector`, `orchestrator`, `finalizer`, `live_collector` (read-only via DB) |

## 14. Observability Layer (Phase 3)

### Overview

The observability layer is a new top-level module (`observability/`) that provides health monitoring, distributed tracing, structured logging, metrics collection, pipeline diagnostics, and incident integration. It follows the existing module conventions (lazy imports, module-level functions, `__init__.py` exports).

### Module Structure

```
observability/
    __init__.py              # Public API exports + initialize_observability()
    config.py                # Environment-based configuration
    models.py                # Data models (HealthReport, Trace, Span, MetricPoint, etc.)
    tracing.py               # TraceContext, TRACE_ID propagation
    logging.py               # JSON structured logging
    metrics.py               # MetricsStore (counters, gauges, histograms)
    utils.py                 # CPU/memory/disk readers

    health/
        __init__.py          # Health registry, get_health(), get_all_health()
        _infrastructure.py   # Oracle VM, Docker, PostgreSQL, TimescaleDB checks
        _collectors.py       # Flashscore, Betting, Player, Registry, Live, Finalizer checks
        _services.py         # Incident Manager, Notification Service checks

    diagnostics/
        __init__.py          # PipelineDefinition, validate_pipeline(), validate_platform()
        _stages.py           # Pipeline definitions (Live Score, Discovery, Odds, Player, Incidents)

    match_monitor.py         # Per-match health tracking
    service_monitor.py       # Service heartbeat tracking
    telegram_diagnostics.py  # Telegram pipeline instrumentation
    incident_integration.py  # Enhanced incident package context
    api.py                   # Public API functions

    tests/
        conftest.py          # Mock database module + test config
        test_tracing.py      # 6 tests
        test_logging.py      # 6 tests
        test_metrics.py      # 8 tests
        test_health.py       # 7 tests
        test_diagnostics.py  # 7 tests
        test_match_monitor.py      # 5 tests
        test_service_monitor.py    # 7 tests
        test_telegram_diagnostics.py # 8 tests
        test_incident_integration.py # 5 tests
        test_api.py          # 9 tests
```

### Component 1 — Health Monitoring

Every service publishes health via `get_health()` returning a `HealthReport` with status, uptime, last_success, last_error, heartbeat, tasks, latency, CPU, and memory. Services register via `register_health_check(name, fn)`.

**Infrastructure checks:** Oracle VM (uptime), Docker (docker info), PostgreSQL (SELECT 1), TimescaleDB (pg_extension).

**Collector checks:** Flashscore Discovery, Betting Discovery, Player Collector, Match Registry, Live Collector, Match Finalizer — each queries its table's MAX(timestamp) and row count.

**Background service checks:** Incident Manager (incidents table), Notification Service (telegram enabled flag).

### Component 2 — Distributed Tracing

`TraceContext` is a context manager that assigns a globally unique TRACE_ID and nested SPAN_ID. Traces propagate through a `contextvars.ContextVar`, supporting nested parent/child spans with depth limits.

```python
with TraceContext("discovery", "orchestrator", "orchestrator.service", "platform"):
    with TraceContext("flashscore_fetch", "collector", "collector.flashscore", "scraping"):
        ...
```

Every span records operation, service, module, component, start/end timestamps, status, and metadata. Complete traces are stored in memory and queryable via `get_trace(trace_id)`.

### Component 3 — Structured Logging

Replaces plain-text `logging.basicConfig()` with JSON-formatted log entries:

```json
{
  "timestamp": "2026-06-29T12:00:00.000+00:00",
  "level": "INFO",
  "logger": "orchestrator.service",
  "message": "Discovery cycle complete",
  "trace_id": "a1b2c3d4e5f6g7h8",
  "span_id": "i9j0k1l2m3n4",
  "service": "orchestrator",
  "component": "platform",
  "metadata": {"match_count": 12}
}
```

The `StructuredLogger` wrapper adds `.operation()` for structured operational logging. A `TraceFilter` injects current trace/span IDs into every record. Falls back to plain-text format when `OBSERVABILITY_LOG_FORMAT=text`.

### Component 4 — Metrics & Telemetry

Thread-safe `MetricsStore` singleton with Counter, Gauge, and Histogram (with percentile snapshots). Queryable via `get_metrics().snapshot()`. Supports up to 100,000 history points.

| Metric type | Methods | Use case |
|-------------|---------|----------|
| Counter | inc(), get(), reset() | Request counts, error counts |
| Gauge | set(), get() | CPU, memory, active connections |
| Histogram | observe(), snapshot() | Latency distributions |

### Component 5 — Pipeline Diagnostics

`PipelineDefinition` defines a named sequence of stages, each with a validator function. `validate_pipeline(name)` runs all stages and reports the first failure with timing.

**Defined pipelines:**

| Pipeline | Stages | Failure detection |
|----------|--------|-------------------|
| Live Score | Flashscore Fetch → Parser → Registry → Collector → Database → Finalizer → Completed Match | Stale/empty tables |
| Discovery | Flashscore Fetch → Betting Site Fetch → Registry | Missing registry entries |
| Odds | Betting Site Fetch → Parser → Registry → Collector → Database | Stale odds data |
| Player Updates | Tennis Explorer Fetch → Parser → Database | Stale player data |
| Incident Creation | Monitor Tick → Detection → Notification | Missing incidents |

### Component 6 — Match Monitoring

`MatchMonitor` tracks every LIVE match independently: score heartbeat, odds heartbeat, tick rates, collection latency, match duration. Generates diagnostics when score/odds updates stop, tick rate drops, or finalizer never executes.

### Component 7 — Service Monitoring

`ServiceMonitor` records heartbeats and tracks service state (RUNNING, IDLE, STOPPED, CRASHED, RESTARTING). Services that miss 3 consecutive heartbeat intervals are reported as STOPPED.

### Component 8 — Telegram Diagnostics

Instruments the complete Telegram pipeline: Message Created → Formatting → Escaping → HTTP Request → Telegram Response → Message ID → Logged. Each stage reports PASS/FAIL with timing, HTTP status, message ID, and error details.

### Component 9 — Incident Integration

`build_diagnostic_context()` generates a comprehensive snapshot: health summary, current metrics, service status, collector status, database status, environment info, and match context. `enhance_incident_package()` writes this to the incident package directory as `observability_context.json`.

### Public API

| Function | Returns |
|----------|---------|
| `get_platform_health()` | Summary of all service health checks |
| `get_service_health(name)` | Detailed health report for one service |
| `get_trace_view(trace_id)` | Complete trace with all spans and timing |
| `validate_platform_pipelines()` | All pipeline validation results |
| `validate_named_pipeline(name)` | Single pipeline validation result |
| `validate_match_pipeline(match_id)` | Per-match pipeline stage analysis |
| `get_platform_metrics()` | All counter/gauge/histogram snapshots |
| `get_recent_telegram_diagnostics()` | Recent Telegram pipeline diagnostics |
| `get_recent_incidents()` | Latest 50 incidents |

### Integration Points

- **Entry points wired:** `main.py` and `run_monitor.py` both call `initialize_observability()` + `setup_structured_logging()` at startup
- **JSON structured logging:** Active by default (`OBSERVABILITY_LOG_FORMAT=json`), falls back to plain text
- **Incident enhancement:** `enhance_incident_package()` called from `package_generator.py` → writes `observability_context.json`
- **System events:** Incident lifecycle events logged to `system_events` TimescaleDB hypertable via `shared/event_logger.py`
- **No changes to existing business logic** — the observability module is entirely additive

## Platform Verification Framework (Phase 3.5)

The Verification Framework answers: **"Can I prove the platform is healthy?"** with evidence-backed reports.

Unlike monitoring ("what's happening now") or testing ("does the code work"), verification produces measurable proof that the platform is functioning correctly in production.

### Architecture
```
verification/
├── __init__.py              # Public API (verify_platform, platform_doctor, etc.)
├── models.py                # VerificationReport, HealthScore, DailyReport, Evidence
├── api.py                   # REST API (verify_infrastructure→collection→pipeline→...)
├── doctor.py                # Platform Doctor (runs all suites, prints summary)
├── health_score.py          # Health Score engine (0–100 with factor weighting)
├── framework/
│   ├── base.py              # BaseVerifier (run(), add_evidence(), _build_report())
│   └── evidence.py          # query_evidence(), sample_rows(), count_rows()
├── validators/
│   ├── infrastructure.py    # VM, Docker, PostgreSQL, TimescaleDB, disk/memory/CPU
│   ├── discovery.py         # Flashscore + betting match counts, duplicates, tournaments
│   ├── registry.py          # Coverage, player/betting mapping %, tracking status
│   ├── collection.py        # Heartbeat, tick frequency, duplicates, score progression
│   ├── database.py          # FK integrity, orphans, duplicates, connections, table stats
│   ├── finalizer.py         # Completion integrity, validation flags, unfinalized matches
│   ├── dataset.py           # Quality score 0–100 (missing data, odds, durations, metadata)
│   ├── incident.py          # Counts, dedup, resolution rate, severity distribution
│   ├── notification.py      # Telegram pipeline stage-by-stage (import → send → delivery)
│   └── pipeline.py          # End-to-end: Flashscore→Parser→Registry→Collector→...→Telegram
├── scheduler/
│   └── scheduler.py         # Async timer: infra 1m, collection 5m, database 15m, doctor daily
├── reports/
│   ├── generator.py         # Daily report with health score, incidents, trends
│   └── storage.py           # JSON archive with load_all(), load_latest(), history
├── cli/
│   └── main.py              # platform verify|doctor|report|health [suite]
└── tests/
    ├── conftest.py           # database module mock (sys.modules)
    ├── test_framework.py     # BaseVerifier, evidence, models
    ├── test_doctor.py        # PlatformDoctor, HealthScoreEngine
    └── test_validators.py    # All validators + API + storage + daily report
```

### Key APIs
| Function | Returns | Purpose |
|----------|---------|---------|
| `verify_platform()` | `list[VerificationReport]` | Run all 9 suites |
| `verify_collection()` | `VerificationReport` | Live match data quality |
| `verify_database()` | `VerificationReport` | FK, orphans, hypertable health |
| `verify_pipeline()` | `VerificationReport` | End-to-end stages with first failure |
| `verify_dataset()` | `VerificationReport` | Quality score 0–100 |
| `platform_doctor()` | `dict` | CLI-friendly overview |
| `get_latest_health_score()` | `HealthScore` | Weighted 0–100 score |
| `generate_daily_report()` | `DailyReport` | Full daily summary |

### Verification Report Structure
Every verification produces:
- `verification_id` — unique UUID
- `verification_type` — which suite
- `started_at / completed_at / duration` — timing
- `status` — PASS / WARNING / FAIL
- `summary` — human-readable result
- `failures / warnings` — issues found
- `metrics` — quantitative evidence
- `recommendations` — suggested actions
- `evidence` — key-value observations with descriptions

### Scheduling
| Suite | Frequency | Rationale |
|-------|-----------|-----------|
| Infrastructure | Every 1 min | System health critical |
| Collection | Every 5 min | Live match data quality |
| Database | Every 15 min | Structural integrity |
| Platform Doctor + Health Score | Daily | Trend tracking |

### Health Score Calculation
Weighted scoring across 9 subsystems:
- Collection (20%), Infrastructure (15%), Database (15%), Pipelines (15%)
- Finalizer (10%), Registry (8%), Discovery (7%), Incidents (5%), Notifications (5%)
- PASS = full weight, WARNING = half, FAIL = zero
- Score stored in `reports/archive/score_history.jsonl` (last 30 entries)

### CLI Commands
```bash
python -m verification.cli platform verify              # All suites
python -m verification.cli platform verify collection   # Single suite
python -m verification.cli platform doctor              # Overview
python -m verification.cli platform report              # Daily report
python -m verification.cli platform health              # Latest score
```

### Testing
18 tests covering framework base, doctor, health score, all validators, API, and report storage. Mock `database` module via `sys.modules` to isolate from PostgreSQL.

## 15. Transformation Metrics

### Integration Status
- `initialize_observability()` called from `main.py` and `run_monitor.py` at startup
- Structured JSON logging active by default (`OBSERVABILITY_LOG_FORMAT=json`), falls back to plain text
- `enhance_incident_package()` called during incident package generation → writes `observability_context.json`
- System events logged to `system_events` hypertable for incident lifecycle, errors, and health changes

| Metric | Before | After |
|--------|--------|-------|
| Largest file | 1,211 lines (telegram_bot.py) | ~200 lines (each handler) |
| Files with module docs | 3 / 47 | 47 / 47 |
| Telegram implementations | 4 (different signatures) | 1 (shared/notify.py) |
| Hardcoded credentials | 3 tokens in source | 0 (all env vars) |
| Observability integration | 0% (orphaned) | 100% (wired, JSON logging active) |
| Player name matching | exact-only (0.2%) | multi-format (93% coverage) |
| Documentation files | 1 (architecture.md) | 5 + 10 ADRs |
| AI config files | 0 | 3 (.ai/) |
| Automation scripts | 0 | 5 (scripts/) |
| Module boundary enforcement | 0 | scripts/validate_module_boundaries.py |

---

## 16. Data Quality Engine (Phase 3.7+)

### Market Matcher (`matcher/`)

Confidence-based multi-signal matching engine replacing name-only fuzzy matching for Flashscore ↔ Betting Site assignment.

**Files:**
| File | Lines | Purpose |
|------|-------|---------|
| `matcher/__init__.py` | 30 | Public API exports |
| `matcher/engine.py` | 320 | Confidence scorer, `match_market()`, `match_all()`, `continuous_retry()` |
| `matcher/signals.py` | 350 | Individual signal extractors |
| `matcher/models.py` | 40 | `MatchAttempt` ORM — persistent attempt log |

**Signals (weighted):**
| Signal | Weight | Description |
|--------|--------|-------------|
| `player_names` | 0.40 | Multi-format: exact, reversed, compound last names, initials, substring |
| `tournament` | 0.20 | City extraction, word matching from tournament string |
| `scheduled_time` | 0.20 | Time proximity (within 1h→4h→same day) |
| `gender` | 0.10 | ATP/WTA/Challenger detection |
| `competition_type` | 0.10 | Qualification vs main draw |

**Confidence levels:** HIGH (≥0.70), MEDIUM (≥0.40), LOW (<0.40), REJECTED (no name match)

**Every candidate receives:** confidence score, signal breakdown, matching explanation, rejection reason. Failed attempts are persisted to `match_attempts` table.

**Public API:**
| Function | Returns | Description |
|----------|---------|-------------|
| `match_market(player1, player2, tournament, time, events)` | `MarketMatchResult` | Score all candidates for one match |
| `match_all(tracked_matches, bt_events)` | `list[MarketMatchResult]` | Batch match with dedup |
| `continuous_retry(session, unmatched, bt_events)` | `int` | Periodic reassignment for unmatched matches |

---

### Live Collector Improvements (Parts 2–4)

**State-Based Score Polling:**
- `MatchState` dataclass tracks set/game/point/server/tiebreak/finished state
- `changed_from(prev)` detects legitimate state transitions (set_changed, game_changed, point_changed, server_changed, match_finished)
- State hash replaces content hash for dedup — only writes on state changes

**Event-Synchronized Odds:**
- When a score state changes (set/game/point/server), the live collector immediately captures the latest odds
- Creates synchronized score+odds events at the same instant
- Standard 3s polling continues as fallback

**Continuous Market Reassignment:**
- Uses `matcher.engine.continuous_retry()` instead of name-only lazy matching
- Runs every 120s for LIVE matches without a betting market
- Timeout: 180 minutes after scheduled start
- Configurable via `matcher/engine.py` constants

---

### Data Repair Engine (`repair/`)

Self-correcting repair pipeline — scans completed matches and repairs recoverable data.

**Never overwrites raw data** (`live_scores`, `live_odds`). Only updates derived fields on `completed_matches`.

**Files:**
| File | Lines | Purpose |
|------|-------|---------|
| `repair/__init__.py` | 25 | Public API exports |
| `repair/engine.py` | 310 | 7 repair handlers, batch processing |
| `repair/classifier.py` | 95 | Failure classification |
| `repair/quality.py` | 170 | Quality scoring A–F |

**Repair Actions:**
| Action | Method | What it fixes |
|--------|--------|---------------|
| `infer_winner` | From final set scores | Missing `winner_player_id`, `final_set_score` |
| `recalculate_duration` | From first score tick to actual finish | Missing/invalid duration |
| `reconstruct_timestamps` | From live_scores/live_odds | Missing first/last timestamps, collection duration |
| `retry_market_assignment` | Retrospective matching | Missing betting_market_id |
| `resolve_player_references` | From tracked_matches | Missing player1_id/player2_id |
| `recompute_validation` | Rerun finalizer validation | Stale validation flags |
| `recalculate_stats` | Rerun stats calculation | Stale tick counts, gaps |

**Orchestration:**
- `run_repairs_on_all(session, cm_list, tm_map)` → processes all completed matches
- Runs every 30 minutes in the orchestrator loop (configurable interval)
- In combination with `run_match_finalizer()`, forms the full post-match pipeline

---

### Failure Classification (`repair/classifier.py`)

Every completed match that fails validation gets exactly one primary failure category:

| Category | Condition |
|----------|-----------|
| `none_needed` | Match passed validation |
| `walkover` / `retirement` / `match_cancelled` | Detected from tournament string |
| `collector_never_started` | Zero score AND zero odds ticks |
| `score_parsing_failed` | 1–2 score ticks (parser couldn't read page) |
| `market_assignment_failed` | Scores present, no odds, no market ID |
| `odds_parsing_failed` | Scores present, no odds, has market ID |
| `collector_started_late` | Some data collected but incomplete |
| `database_write_failed` | Data collected but not persisted |
| `flashscore_unavailable` / `betting_site_unavailable` | Source was down |
| `unknown` | Rare edge cases |

Stored in `completed_matches.failure_category` column.

---

### Quality Scoring (`repair/quality.py`)

A–F grade computed from 5 weighted factors:

| Factor | Weight | Basis |
|--------|--------|-------|
| Score completeness | 0.25 | Unique states vs expected, or tick count tiers |
| Odds completeness | 0.25 | Tick count tiers (200+/100+/50+/10+) |
| Timeline completeness | 0.15 | Deductions for missing start/finish/duration timestamps |
| Synchronization | 0.20 | Odds-at-score coverage % |
| Validation | 0.15 | 100 if passed, 50 if partial, 0 if no data |

| Grade | Range |
|-------|-------|
| A | 90+ |
| B | 75–89 |
| C | 50–74 |
| D | 25–49 |
| F | 0–24 |

Stored in `completed_matches.quality_grade` and `.quality_score`.

---

### Reports (`reports/`)

Report generation for data quality monitoring:

| Report | Key metrics |
|--------|-------------|
| `MarketMatchingReport` | % with market, by confidence level, top rejection reasons |
| `OddsCoverageReport` | Coverage %, avg ticks, by tournament |
| `CollectionReport` | Score/odds averages, validation pass %, by day |
| `RepairReport` | Repaired vs unchanged, fixes by action type |
| `FailureDistributionReport` | Failure categories, unknown count |
| `DatasetQualityReport` | A–F distribution, avg quality score |
| `ReplayReadinessReport` | % ready, list of top-quality replay candidates |

Generated via `reports.generate_all_reports(session)`.

---

### Database Schema Additions

**`completed_matches` — new columns:**
| Column | Type | Purpose |
|--------|------|---------|
| `score_completeness_pct` | FLOAT | Score data completeness % |
| `odds_completeness_pct` | FLOAT | Odds data completeness % |
| `timeline_completeness_pct` | FLOAT | Timeline completeness % |
| `synchronization_score` | FLOAT | How well odds align with score events |
| `quality_grade` | VARCHAR(2) | A/B/C/D/F grade |
| `quality_score` | FLOAT | 0–100 weighted quality score |
| `failure_category` | VARCHAR(64) | Primary failure category |
| `failure_reason` | VARCHAR(1024) | Detailed failure explanation |
| `market_assigned_at` | TIMESTAMPTZ | When market was assigned |
| `collector_started_at` | TIMESTAMPTZ | When first data was collected |
| `collector_finished_at` | TIMESTAMPTZ | When collector detected finish |
| `repair_actions` | VARCHAR(1024) | Which repairs were applied |
| `repair_count` | INTEGER | How many times repaired |
| `last_repaired_at` | TIMESTAMPTZ | Last repair timestamp |

**`tracked_matches` — new columns:**
| Column | Type | Purpose |
|--------|------|---------|
| `market_assigned_at` | TIMESTAMPTZ | When market was matched |
| `collection_started_at` | TIMESTAMPTZ | When live polling began |

**New table: `match_attempts`**
| Column | Type | Purpose |
|--------|------|---------|
| `id` | INT PK | Auto-increment |
| `flashscore_match_id` | VARCHAR(32) | Which Flashscore match |
| `betting_market_id` | VARCHAR(64) | Candidate market ID |
| `player1_name`, `player2_name` | VARCHAR(255) | Match players |
| `tournament` | VARCHAR(255) | Tournament name |
| `confidence_score` | FLOAT | 0.0–1.0 confidence |
| `confidence_level` | VARCHAR(16) | HIGH/MEDIUM/LOW/REJECTED |
| `signal_scores` | JSON | Per-signal score breakdown |
| `signal_reasons` | JSON | Per-signal explanation |
| `selected` | BOOLEAN | Was this candidate chosen |
| `rejected` | BOOLEAN | Was this candidate rejected |
| `rejection_reason` | VARCHAR(512) | Why rejected |
| `created_at` | TIMESTAMPTZ | When attempt was made |

---

## 17. Historical Reprocessing

After deployment, the repair engine automatically processes all existing completed matches:
1. Loads all `completed_matches` + `tracked_matches`
2. Runs all 7 repair actions on each
3. Classifies failure for each non-passing match
4. Computes A–F quality grade for every match
5. Generates before/after statistics via logs
6. Re-runs every 30 minutes to catch newly finalized matches

No recollection required. All repairs are idempotent and logged.

---

## 18. Developer Console (Phase 4)

### Overview

Internal engineering console for debugging, analyzing, inspecting, monitoring, validating, verifying, and improving every part of the platform. A developer should never need to SSH into the server, inspect database tables manually, or search log files to understand what happened.

### Architecture

```
┌──────────────────────────────┐     ┌───────────────────────────────┐
│  console/ (Next.js 14)       │────▶│  console_api/ (FastAPI)       │
│  Port 3000                   │     │  Port 8000                    │
│                              │     │                               │
│  TypeScript                  │     │  Python 3.12                  │
│  TailwindCSS                 │     │  38 REST endpoints            │
│  shadcn/ui components        │     │  WebSocket /ws/live           │
│  TanStack Query              │     │  Read-only TimescaleDB access │
│  AG Grid                     │     │                               │
│  React Flow                  │     │  Docker container             │
│  Recharts                    │     │  restart: always              │
└──────────────────────────────┘     └───────────────┬───────────────┘
                                                     │
                                              ┌──────▼──────┐
                                              │ TimescaleDB │
                                              │  (PostgreSQL 16)        │
                                              └─────────────┘
```

### Backend: `console_api/`

FastAPI service with 38 REST endpoints + WebSocket for live updates.

**Files:**
| File | Purpose |
|------|---------|
| `console_api/main.py` | FastAPI app, CORS, lifespan, route registration |
| `console_api/deps.py` | DB session, pagination, time range dependencies |
| `console_api/models.py` | Pydantic response models (PlatformOverview, MatchDetail, etc.) |
| `console_api/ws.py` | WebSocket endpoint `/ws/live` with broadcast support |
| `console_api/routers/` | 18 route modules (1 per module) |

**Route Modules:**
| Module | Endpoints | Purpose |
|--------|-----------|---------|
| `overview` | `/api/overview` | Platform health, counts, percentages |
| `matches` | `/api/matches`, `/api/matches/live`, `/api/matches/{id}`, `/api/matches/{id}/scores`, `/api/matches/{id}/odds`, `/api/matches/{id}/timeline` | Match CRUD, scores, odds, timeline |
| `collectors` | `/api/collectors` | Collector statuses |
| `matching` | `/api/matching/summary`, `/api/matching/attempts`, `/api/matching/unmatched` | Market matching stats |
| `discovery` | `/api/discovery/summary`, `/api/discovery/runs` | Discovery cycles |
| `registry` | `/api/registry/summary`, `/api/registry/players` | Registry stats |
| `database` | `/api/db/tables`, `/api/db/table/{name}` | DB table browser |
| `quality` | `/api/quality/distribution`, `/api/quality/failures` | Quality grades |
| `validation` | `/api/validation/summary` | Validation pass/fail |
| `verification` | `/api/verification/health-score-history` | Verification history |
| `observability` | `/api/observability/health`, `/api/observability/metrics` | Service health |
| `pipeline` | `/api/pipeline/status` | Pipeline stage status |
| `incidents` | `/api/incidents`, `/api/incidents/{id}` | Incident management |
| `repair` | `/api/repairs/summary`, `/api/repairs/history` | Repair history |
| `reports` | `/api/reports/all`, `/api/reports/{name}` | All 6 report types |
| `analytics` | `/api/analytics/trends` | Daily trend data |
| `search` | `/api/search?q=` | Global search |
| `timeline` | `/api/timeline` | System events timeline |

### Frontend: `console/`

Next.js 14 App Router with TypeScript, TailwindCSS, and custom component library.

**Navigation Sections:**
| Section | Pages |
|---------|-------|
| Monitor | Overview, Live Matches, Match Explorer, Collectors |
| Pipeline | Market Matching, Discovery, Registry, Database |
| Quality | Dataset Quality, Validation, Verification, Reports |
| Observability | Observability, Pipeline, Incidents, Repair |
| Tools | Analytics, Global Search, Timeline, Logs |

**Key Components:**
| Component | Type | Description |
|-----------|------|-------------|
| `Sidebar` | Layout | 280px fixed sidebar, 5 sections, 19 nav links |
| `StatCard` | Layout | Metric card with value, trend, icon, color |
| `DataTable` | Data | AG Grid wrapper — dark theme, pagination, sorting |
| `MatchCard` | Data | Live match card with scores, odds, quality |
| `ScoreTimeline` | Chart | Recharts line chart for game score progression |
| `Button` | UI | 4 variants, 3 sizes |
| `Card` | UI | Card with header, content, footer |
| `Badge` | UI | 5 severity/status variants |
| `Input` | UI | Styled text input |
| `Select` | UI | Styled select dropdown |
| `Tabs` | UI | Controlled/uncontrolled tabs |

**Shared Libraries:**
| File | Purpose |
|------|---------|
| `lib/api.ts` | 27 typed API functions + all TypeScript interfaces |
| `lib/websocket.ts` | WebSocket client with auto-reconnect |
| `lib/utils.ts` | cn(), formatDate(), statusColor(), qualityColor(), etc. |

### Deployment

The console_api runs as a separate Docker container:
- **Image:** `Dockerfile.console_api` (Python 3.12-slim + FastAPI + uvicorn)
- **Port:** 8000 (exposed on host)
- **Healthcheck:** DB connectivity check every 30s
- **Restart:** always

The console frontend builds to static files served by Next.js (port 3000) — can be deployed via Vercel, nginx, or the Oracle VM directly.

### Key Pages

**Dashboard (`/`):** 8 StatCards (total matches, live matches, quality score, incidents, score/odds ticks, validation %, replay %), quality distribution bars, live match previews.

**Live Matches (`/matches/live`):** 5s auto-refreshing grid of MatchCards with scores and odds.

**Match Explorer (`/matches/[id]`):** 8-tab comprehensive view — Overview, Scores, Odds, Timeline (chart), Completed (validation, quality), Incidents, Match Attempts, Repairs. Every piece of data about a single match.

**Database Explorer (`/database`):** Browse tables, click to view rows.

**Pipeline Explorer (`/pipeline`):** Vertical stepper showing Discovery → Registry → Matching → Collectors → DB → Finalizer → Repair → Completed.

**Incident Manager (`/incidents`):** DataTable with modal detail view.

**Reports (`/reports`):** All 6 report types as cards with key stats.

### Cross-Linking

Every object links to related objects:
- Match → Incidents → Repair → Match Attempts → Database rows
- Incident → Related Match → Pipeline stage → Collector status
- No dead ends — every page connects to related data.

---

## 18. Developer Console (Next.js 14)

A FastAPI-powered web console at `console/` for monitoring, exploring, and debugging the platform.

**Stack:** Next.js 14, React 18, TanStack Query 5, TypeScript, Tailwind CSS, AG Grid, Recharts

### Page inventory (21 pages)

| # | Route | Page | API dependency |
|---|-------|------|---------------|
| 1 | `/` | Dashboard / Overview | `api.overview()`, `api.liveMatches()` |
| 2 | `/matches` | Match Explorer | `api.searchMatches(params)` |
| 3 | `/matches/live` | Live Matches | `api.liveMatches()` (5s poll) |
| 4 | `/matches/[id]` | Match Detail | `api.matchDetail(id)`, `api.matchScores(id)`, `api.matchOdds(id)` |
| 5 | `/collectors` | Collector Explorer | `api.collectors()` (10s poll) |
| 6 | `/matching` | Market Matching | `api.matchingSummary()`, `api.matchingUnmatched()`, `api.matchingAttempts(params)` |
| 7 | `/discovery` | Discovery Explorer | `api.discoverySummary()` |
| 8 | `/registry` | Registry Explorer | `api.registrySummary()` |
| 9 | `/database` | Database Explorer | `api.dbTables()`, `api.dbTable(name)` |
| 10 | `/quality` | Dataset Quality | `api.qualityDistribution()`, `api.qualityFailures()` |
| 11 | `/validation` | Validation Explorer | `api.validationSummary()` |
| 12 | `/verification` | Verification Explorer | `api.verificationHistory()` |
| 13 | `/observability` | Observability | `api.observabilityHealth()` |
| 14 | `/pipeline` | Pipeline Stages | `api.pipelineStatus()` |
| 15 | `/incidents` | Incident Manager | `api.incidents(params)` |
| 16 | `/repair` | Repair Explorer | `api.repairsSummary()` |
| 17 | `/reports` | Reports | `api.reports()` |
| 18 | `/analytics` | Analytics | `api.analyticsTrends()` |
| 19 | `/search` | Global Search | `api.search(q)` |
| 20 | `/timeline` | Global Timeline | `api.timeline()` |
| 21 | `/logs` | System Logs | `api.timeline()` with filters |

### Component library

| Component | Path | Purpose |
|-----------|------|---------|
| `StatCard` | `components/layout/StatCard.tsx` | Metric display with trend indicator |
| `Sidebar` | `components/layout/Sidebar.tsx` | 5-section navigation |
| `DataTable` | `components/data/DataTable.tsx` | AG Grid wrapper for tabular data |
| `MatchCard` | `components/data/MatchCard.tsx` | Compact match card with live scores |
| `ScoreTimeline` | `components/charts/ScoreTimeline.tsx` | Recharts line chart for game scores |
| `Button`, `Badge`, `Card`, `Input`, `Select`, `Tabs` | `components/ui/` | Primitive UI components |

### API layer (`lib/api.ts`)

All API calls go through `fetchAPI<T>(path, params)` which targets `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`). Returns typed interfaces matching the backend models.

### Patterns

- Every page starts with `"use client"` and uses TanStack Query `useQuery`
- Loading states shown as "Loading..." text; empty states shown as "No data" message
- Auto-polling via `refetchInterval` for live/batch pages
- Static navigation via `next/link`; programmatic routing via `useRouter().push()`
- Dark theme: slate-950 background, slate-800 borders, emerald accent

## 19. Score Collection Improvements (Phase A) & Point Collection (Phase B)

### Phase A — Score Gap Fixes
- **Poll interval** reduced from 10s to **5s** (config.py, docker-compose)
- **Per-set game history** parsed from detail-tab-content on every poll
- **Gap detection**: when game score changes by >1, interpolated states inserted with `source='interpolated'`  
- **Set history ticks**: completed set game scores stored as `source='set_history'`
- **LiveScore.source** column: `'polled'` | `'interpolated'` | `'set_history'`

### Phase B — Point-by-Point Collection
- **LivePoint** model: hypertable with set_number, game_number, point_a/b, point_string, server_name, BP/SP/MP flags
- **Flashscore JSON feed**: `d_hh_{match_id}_en_1` endpoint parsed for point-level state
- **Point polling** every 3s for matches with betting markets
- **Console**: Points tab on Match Explorer with PointTimeline component
- **API**: `GET /api/matches/{id}/points` endpoint

