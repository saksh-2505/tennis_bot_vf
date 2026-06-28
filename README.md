# Sports Trading Platform V3

Live tennis data collection, replay, research, backtesting, and execution.

**Database:** PostgreSQL 16 + TimescaleDB (hypertables for time-series)

## Quick Start

```bash
docker compose up -d      # Start TimescaleDB
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

python main.py            # Starts discovery + status monitor + live collection
```

## Project Structure

```
collector/          Data collection (Flashscore + betting site + Tennis Explorer)
registry/           Match Registry — canonical match records
orchestrator/       Platform orchestrator — runtime loop
live_collector/     Live score & odds collection  ★ Phase 2
models/             ORM models (TimescaleDB hypertables)
tests/              Test suite
storage/ replay/ research/ backtest/ execution/ dashboard/   (stubbed)
```

## Platform (orchestrator/service.py)

**Status Monitor** — runs every 5 min, DB-only, transitions DISCOVERED → LIVE:
- Reads `tracked_matches` where `status=DISCOVERED`
- If `scheduled_start <= now_utc` → sets `status=LIVE`

**Discovery** — scrapes twice a day (every 12 h):
- Flashscore → Betting Site → new Players → Match Registry

## Live Collection  ★ Phase 2

Background daemon thread polls scores and odds for every LIVE match:

| Scraper | Table | Interval | Writes |
|---------|-------|----------|--------|
| Flashscore scores | `live_scores` (hypertable) | 10 s | Only on score change |
| Betting site odds | `live_odds` (hypertable) | 2 s | Only if ≥1 odds non-NULL and changed |

Both tables are TimescaleDB hypertables partitioned by `timestamp` (1-day chunks, compressed after 7 days). Data is retained forever for ML training. Dedup via `content_hash` — matching ticks are silently skipped via `ON CONFLICT DO NOTHING`.

Finish detection: when Flashscore marks a match finished, the collector updates `tracked_matches.status = "FINISHED"` and calculates `match_duration_min`.

## Configuration

Copy `.env.example` to `.env` and adjust values.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://...` | PostgreSQL/TimescaleDB connection |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FORMAT` | `text` | Log output format |
| `DISCOVERY_ENABLED` | `true` | Enable scheduled discovery |
| `DISCOVERY_INTERVAL_SECONDS` | `43200` | Discovery cycle (12 h) |
| `STATUS_CHECK_INTERVAL_SECONDS` | `300` | Status monitor poll (5 min) |
| `LIVE_SCORE_INTERVAL_SECONDS` | `10` | Score poll interval |
| `LIVE_ODDS_INTERVAL_SECONDS` | `2` | Odds poll interval |
| `LIVE_PREFETCH_MINUTES` | `5` | Pre-fetch URL before start |

## Development

```bash
pip install -e ".[dev]"
pytest
```
