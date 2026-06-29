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

## Technical Debt

| Item | Impact | Target |
|------|--------|--------|
| No foreign key constraints in DB | Data integrity risk | Phase 5 |
| Empty stub modules (backtest, replay, etc.) | Confusing structure | Phase 5 |
| `incidents/telegram_bot.py` at 1,211 lines | High context cost per edit | Phase 2 |
| 3 separate Telegram implementations | Fragmented error handling | Phase 2 |
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
