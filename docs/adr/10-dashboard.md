# ADR 10: Dashboard — Why Delayed

## Problem
Need a web interface for monitoring and analysis.

## Decision
Dashboard development delayed until Phases 9-10. Current incidents module and Telegram bot cover monitoring needs.

## Alternatives
- **FastAPI + Vue.js**: Full web stack; requires frontend expertise
- **Streamlit**: Rapid prototyping; not suitable for production
- **Grafana**: Connects to TimescaleDB directly; no custom code needed

## Tradeoffs
- + Lower development cost now (focus on collection quality)
- + Grafana is a strong candidate for Phase 9
- + Telegram bot already provides query capabilities
- - No visual match analysis yet
- - Manual SQL queries for custom analysis
- - Dashboard module is an empty stub

## Consequences
- `dashboard/` module is empty
- All current monitoring via Telegram bot + `docker logs`
- Grafana preferred for Phase 9 (native TimescaleDB support)
- .ai/scripts can generate ad-hoc analysis context
