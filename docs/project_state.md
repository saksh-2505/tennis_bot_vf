# Project State

## Completed

- Match discovery (Flashscore + Betting Site)
- Player profiles (Tennis Explorer)
- Match registry (Flashscore ↔ Betting Site matching)
- Live score/odds collection (10s/2s polling)
- Match finalization (stats, validation, completed_matches)
- Incident management (detection, packages, recovery, auto-resolve)
- Telegram bot (23 commands: matches, players, live data, system)
- Production deployment (Oracle Cloud, 3 Docker containers)
- TimescaleDB hypertables with compression

## Active

- Live system running on Oracle Cloud
- Incident monitor polling every 60s
- Discovery cycle every 12h
- Status monitor every 5min

## Known Issues

| Issue | Status | Priority |
|-------|--------|----------|
| No matching Flashscore bet for some betting markets (name mismatch) | Monitoring | Low |
| Betting site 429 rate limits during discovery | Mitigated (retry/backoff) | Low |
| Flashscore mobile parser returns empty for some match pages | Monitoring | Low |
| No tests for Telegram bot handlers | Open | Medium |
| Hardcoded credentials in `monitor/tennis_bot_monitor.py` | Fixed | High |

## Recently Fixed (2026-07-01)

| Issue | Fix |
|-------|-----|
| Observability layer disconnected | Wired `initialize_observability()` into both entry points; connected `enhance_incident_package()` into package generator; enabled JSON structured logging |
| No log persistence for post-mortem | Created `system_events` hypertable for structured event logging (incidents, errors, health events) |
| Incident packages missing Docker logs in containers | Added shared log volume `shared_logs` mounted at `/app/logs` on both containers |
| 3 separate Telegram implementations | Consolidated all outbound Telegram calls through `shared/notify.py` |
| No healthchecks on app/monitor containers | Added Docker healthchecks: DB connectivity check for app, process check for monitor |
| 6 stub modules with minimal docstrings | Expanded docstrings explaining planned purpose and phase for backtest, dashboard, execution, replay, research, storage |
| Documentation outdated on observability and credentials | Updated architecture.md to reflect wired-in observability, no hardcoded tokens, shared log volume |

## Technical Debt

| Item | Impact | Target |
|------|--------|--------|
| No foreign key constraints in DB | Data integrity risk | Phase 5 |
| Stub modules have limited implementation | Not usable yet | Phase 4+ |
| `incidents/telegram_bot/` split across 7 files | Moderate context cost | Ongoing |
| No `contributing.md` | Inconsistent new contributions | Phase 4 |

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Match Discovery | ✅ Complete |
| 2 | Live Data Collection | ✅ Complete |
| 3 | Incident Management | ✅ Complete |
| 4 | Replay System | 🔄 Stubbed |
| 5 | Research | 🔄 Stubbed |
| 6 | Backtesting | 🔄 Stubbed |
| 7 | Predictions | 🔄 Planned |
| 8 | Execution | 🔄 Planned |
| 9 | Dashboard | 🔄 Planned |
| 10 | Production Hardening | 🔄 Ongoing |
