# AI Development Rules

These rules are loaded at the start of every AI-assisted session.

## Before Writing Code

- **Search before writing.** Check existing files, interfaces, and patterns before creating anything new.
- **Read the `docs/code_index.md`** to find the correct module for your change.
- **Read the module's README** (if exists) for API and ownership.
- **Check existing tests** in `tests/` for patterns and fixtures.

## When Writing Code

- **Never duplicate code.** If a utility exists in `shared/`, import it. If it doesn't exist and you need it in 2+ places, add it to `shared/`.
- **Keep interfaces stable.** Do not rename or change signatures of public API functions without updating all callers and docs.
- **Use `_e = html.escape` for Telegram output.** All user-facing strings must be HTML-escaped.
- **Write tests.** Every new function needs a test in the corresponding test file.
- **Use `_` prefix for internal helpers.** Module-private functions that are not part of the public API must start with `_`.
- **Prefer composition over inheritance.** No deep class hierarchies.
- **Minimize context.** Keep files under 300 lines. If a file exceeds 300 lines, split it by concern.

## Data Integrity

- **Never silently change DB schemas.** Schema changes require `init_db()` update and documented migration.
- **Validate input.** Collector parsers must handle malformed HTML gracefully (return empty list, log warning).
- **Handle rate limits.** External API calls must have retry with backoff.
- **DB sessions must be closed.** Use context managers (`with SessionLocal() as session:`).

## After Writing

- **Update documentation.** If you changed a public API, update `docs/code_index.md`, the module README, and `docs/architecture.md`.
- **Update `docs/project_state.md`** with any new known issues or technical debt.
- **Run existing tests.** `python -m pytest tests/ -q` before pushing.
- **Commit messages format:** `module: brief description` (e.g., `collector.flashscore: fix date parsing for mobile titles`).

## Incremental Development

- **One concern per change.** Do not fix unrelated issues in the same commit.
- **Independent deploys.** Each PR should be independently deployable.
- **Backward compatibility.** Do not break existing APIs unless absolutely necessary, and document any breaks.
