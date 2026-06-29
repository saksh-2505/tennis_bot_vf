# Code Index

Every subsystem with purpose, public API, dependencies, and consumers.

---

## Collector — Flashscore

| Field | Value |
|-------|-------|
| **Purpose** | Discover tennis matches from flashscore.mobi |
| **Folder** | `collector/flashscore/` |
| **Public API** | `discover_matches()`, `save_matches_to_db()` |
| **Entry Points** | `__init__.py:discover_matches()` |
| **Important Files** | `client.py` (HTTP), `parser.py` (HTML→Match), `__init__.py` (orchestration) |
| **DB Tables** | `flashscorefoundmatches` |
| **Dependencies** | `database.SessionLocal`, `models.flashscore.FlashscoreFoundMatch` |
| **Consumers** | `orchestrator.service.run_discovery_cycle()` |
| **External APIs** | `flashscore.mobi` (HTTP GET) |

---

## Collector — Betting Site

| Field | Value |
|-------|-------|
| **Purpose** | Discover betting markets for tennis matches |
| **Folder** | `collector/betting_site/` |
| **Public API** | `discover_matches(fs_matches)`, `save_matches_to_db()` |
| **Entry Points** | `__init__.py:discover_matches()` |
| **Important Files** | `client.py` (HTTP+retry), `parser.py` (JSON→Match), `__init__.py` (orchestration) |
| **DB Tables** | `bettingsitefoundmatches` |
| **Dependencies** | `database.SessionLocal`, `models.bettingsite.BettingsiteFoundMatch`, `collector.flashscore.parser.Match` |
| **Consumers** | `orchestrator.service.run_discovery_cycle()` |
| **External APIs** | `odd.ocric99.com`, `api.dcric99.com` (HTTP POST) |

---

## Collector — Tennis Explorer

| Field | Value |
|-------|-------|
| **Purpose** | Fetch player profiles (rankings, stats, surface history) |
| **Folder** | `collector/tennis_explorer/` |
| **Public API** | `update_players(names)`, `update_player(name)` |
| **Entry Points** | `__init__.py:update_players()` |
| **Important Files** | `client.py` (HTTP), `parser.py` (HTML→PlayerData), `__init__.py` (DB upsert) |
| **DB Tables** | `players` |
| **Dependencies** | `database.SessionLocal`, `models.player.Player` |
| **Consumers** | `orchestrator.service._update_missing_players()` |
| **External APIs** | `tennisexplorer.com` (HTTP GET) |

---

## Registry

| Field | Value |
|-------|-------|
| **Purpose** | Cross-reference Flashscore matches with Betting Site markets |
| **Folder** | `registry/` |
| **Public API** | `build_match_registry()` |
| **Entry Points** | `service.py:build_match_registry()` |
| **DB Tables** | `tracked_matches` |
| **Dependencies** | `database.engine`, `models.tracked_match.TrackedMatch`, `models.flashscore.*`, `models.bettingsite.*`, `models.player.*` |
| **Consumers** | `orchestrator.service.run_discovery_cycle()` |

---

## Orchestrator

| Field | Value |
|-------|-------|
| **Purpose** | Main platform loop: discovery → status monitor → finalizer |
| **Folder** | `orchestrator/` |
| **Public API** | `run_platform()`, `update_match_statuses()`, `run_discovery_cycle()` |
| **Entry Points** | `service.py:run_platform()` |
| **DB Tables** | `tracked_matches` (via models) |
| **Dependencies** | All collector modules, registry, finalizer, live_collector, config |
| **Consumers** | `main.py` |

---

## Live Collector

| Field | Value |
|-------|-------|
| **Purpose** | Poll live scores (10s) and odds (2s) for LIVE matches |
| **Folder** | `live_collector/` |
| **Public API** | `run_live_collection_loop()`, `get_heartbeat()` |
| **Entry Points** | `service.py:run_live_collection_loop()` |
| **DB Tables** | `live_scores`, `live_odds` (hypertables) |
| **Dependencies** | `models.tracked_match.TrackedMatch`, `config`, `live_collector.flashscore_live`, `live_collector.betting_live` |
| **Consumers** | `orchestrator.service._spawn_live_collector()` |

---

## Finalizer

| Field | Value |
|-------|-------|
| **Purpose** | Finalize finished matches: calculate stats, validate, store |
| **Folder** | `finalizer/` |
| **Public API** | `finalize_match(session, id)`, `run_match_finalizer(session)` |
| **Entry Points** | `service.py:run_match_finalizer()` |
| **Important Files** | `service.py` (orchestration), `stats.py` (computations), `validation.py` (quality checks), `telegram.py` (notifications) |
| **DB Tables** | `completed_matches` |
| **Dependencies** | `models.tracked_match.*`, `models.live_score.*`, `models.live_odds.*`, `models.completed_match.*` |
| **Consumers** | `orchestrator.service._run_finalizer()` |

---

## Incidents

| Field | Value |
|-------|-------|
| **Purpose** | Detect, track, recover from system anomalies |
| **Folder** | `incidents/` |
| **Public API** | `monitor_platform()`, `create_incident()`, `resolve_incident()`, `get_open_incidents()`, `generate_incident_package()`, `send_notification()`, `attempt_recovery()`, `check_commands()` |
| **Entry Points** | `__init__.py:monitor_platform()` (called from `run_monitor.py`), `telegram_bot.py:check_commands()` (called from monitor tick) |
| **Important Files** | `monitor.py` (health checks), `service.py` (CRUD), `package_generator.py` (diagnostic bundles), `telegram_bot/` (23 commands) |
| **DB Tables** | `incidents` |
| **Dependencies** | `database.SessionLocal`, `incidents.config`, `incidents.models.Incident` |
| **Consumers** | `run_monitor.py` (Docker monitor container) |

---

## Models

| Field | Value |
|-------|-------|
| **Purpose** | SQLAlchemy ORM models and data classes |
| **Folder** | `models/` |
| **Important Files** | `player.py` (84 lines, ~40 columns), `completed_match.py` (97 lines, ~35 columns), `tracked_match.py` (49 lines), `collector_match.py` (shared dataclass) |
| **DB Tables** | 8 tables (see `docs/database.md`) |
| **Dependencies** | `database.Base` |

---

## Shared Utilities

| Field | Value |
|-------|-------|
| **Purpose** | Reusable components to eliminate duplicate code |
| **Folder** | `shared/` |
| **Important Files** | `notify.py` (Telegram sender), `httpx_client.py` (HTTP with retry) |
| **Dependencies** | None |
| **Consumers** | All modules requiring HTTP or Telegram |

---

## External APIs

| API | URL | Used By | Purpose |
|-----|-----|---------|---------|
| Flashscore Mobile | `flashscore.mobi` | Collector | Match listing + score pages |
| Flashscore Desktop | `flashscore.com` | Collector | Match detail pages (fallback) |
| Betting Site Odds | `odd.ocric99.com` | Collector + Live | Market data |
| Betting Site Events | `api.dcric99.com` | Collector + Live | Event metadata |
| Tennis Explorer | `tennisexplorer.com` | Collector | Player profiles |
| Telegram Bot API | `api.telegram.org` | Incidents + Finalizer | Bot commands + notifications |
