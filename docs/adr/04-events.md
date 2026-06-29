# ADR 4: Events — Why No Event Bus

## Problem
Need to coordinate between discovery, live collection, finalization, and incident detection.

## Decision
No formal event bus. Use synchronous function calls and DB-based state polling instead.

## Alternatives
- **RabbitMQ/Redis pub-sub**: Adds infrastructure, increases deployment complexity, overkill for current scale
- **SQLAlchemy events**: Tight coupling to ORM lifecycle, hard to debug
- **Polling DB**: Simple, testable, no additional infrastructure

## Tradeoffs
- + Zero additional infrastructure
- + Simple to understand and debug
- + DB acts as durable event store
- - Synchronous calls block the main loop
- - Asyncio only in live collector (daemon thread)
- - No publish-subscribe pattern for future consumers

## Consequences
- `orchestrator/service.py` orchestrates phases sequentially
- `incidents/monitor.py` polls DB for stale conditions
- Live collector runs in a daemon thread with its own session
- Future: adopt polling-based event pattern (DB as message queue)
