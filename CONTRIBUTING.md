# Contributing

## Repository structure

```
sports-trading/
├── collector/          # Data collectors (Flashscore, Betting Site, Tennis Explorer)
├── finalizer/          # Match finalization pipeline
├── incidents/          # Incident detection, management, Telegram bot
├── live_collector/     # Live score + odds polling
├── models/             # ORM models + shared dataclasses
├── monitor/            # External health monitor (cron-based)
├── orchestrator/       # Main platform loop
├── registry/           # Match registry (Flashscore ↔ Betting Site)
├── shared/             # Reusable utilities (HTTP, notifications)
├── docs/               # Documentation, ADRs, code index
├── scripts/            # AI context engine + automation
├── tests/              # Test files (one per module)
├── .ai/                # AI rules, agent definitions, context config
└── main.py             # Entry point
```

## Coding Standards

- **Python 3.12+** with type hints on all function signatures
- **SQLAlchemy 2.x** ORM models (declarative base)
- **httpx** for HTTP (Client for sync, AsyncClient for async)
- **BeautifulSoup4** for HTML parsing
- **Pydantic Settings** for configuration

## Naming

| Element | Convention | Example |
|---------|------------|---------|
| Files | `snake_case.py` | `live_collector.py` |
| Functions | `snake_case()` | `discover_matches()` |
| Classes | `PascalCase` | `TrackedMatch` |
| Constants | `SCREAMING_SNAKE` | `MAX_RESULTS` |
| Private | `_leading_underscore` | `_normalize_name()` |
| Tests | `test_snake_case.py` | `test_live_collector.py` |

## Module Organization

Each module should have:
- **`__init__.py`** — re-exports the public API
- **`service.py`** — orchestration logic (if >50 lines)
- **`client.py`** — external HTTP APIs (if applicable)
- **`parser.py`** — response parsing (if applicable)

Keep files under 300 lines. If a file exceeds this, split by concern.

## Typing

- All function signatures typed: `def func(arg: str) -> list[int]:`
- `from __future__ import annotations` in all files
- Use `| None` instead of `Optional`
- SQLAlchemy models use `Mapped[type]` syntax

## Logging

```python
import logging
logger = logging.getLogger(__name__)

logger.debug("detail")  # development
logger.info("summary")  # prod events
logger.warning("concern")  # non-critical
logger.exception("error")  # exceptions always
```

## Async

- Async only in `live_collector/service.py` (asyncio.gather for concurrent polling)
- All other modules use synchronous code
- Live collector runs in a daemon thread via `asyncio.run()`

## Error Handling

- `except Exception` at module boundaries only (collector, monitor)
- Specific exceptions in business logic (`AlreadyFinalized`, `NotFinished`)
- `logger.exception()` inside except blocks
- Retry with backoff for external API calls

## Testing

- Use `pytest` with in-memory SQLite (patched `SessionLocal`)
- One test file per module: `tests/test_{module}.py`
- Mock external HTTP with inline HTML/JSON fixtures
- Test both success and error cases

## Review Checklist

Before submitting:
- [ ] Code compiles without errors
- [ ] Tests pass: `python -m pytest tests/ -q`
- [ ] Public API is unchanged (or documented if changed)
- [ ] New functions have type hints and docstrings
- [ ] No hardcoded secrets (tokens, passwords)
- [ ] Module docstring updated
- [ ] `docs/code_index.md` reflects any API changes
- [ ] Logged warnings for degraded behavior, errors for failures

## Migration Rules

- Schema changes: additive only (no destructive ALTERs)
- Config changes: backward-compatible defaults
- Module splits: keep backward-compatible `__init__.py` re-exports
- Never commit `.env` or secrets to the repository

## Documentation Requirements

Every Python file must have:
```python
"""Module purpose.

Public API:
    - function_name(): description

Dependencies:
    - module_name: reason
"""
```

Every public function must have a docstring describing:
- Purpose (1 sentence)
- Args
- Returns
- Raises (if any)

## Commit Message Format

```
module: brief description

Optional detailed explanation (72 char wrap).
```

Examples:
```
collector.flashscore: fix date parsing for mobile titles

extract_match_datetime() now searches <div class="detail"> elements
for dd.mm.yyyy HH:MM patterns instead of relying on <title> tags
which no longer contain dates.
```

```
incidents.telegram_bot: split into sub-modules

Bot handlers now live in incidents/telegram_bot/ split by domain
(match, player, live, system). check_commands() re-exported from
init for backward compatibility.
```
