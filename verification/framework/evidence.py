"""Evidence collection helpers."""
from __future__ import annotations

from typing import Any

from database import SessionLocal
from sqlalchemy import text


def query_evidence(session, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    result = session.execute(text(sql), params or {})
    return [dict(row._mapping) for row in result]


def sample_rows(table: str, limit: int = 5) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        return query_evidence(session, f"SELECT * FROM {table} ORDER BY RANDOM() LIMIT :limit", {"limit": limit})


def count_rows(table: str) -> int:
    with SessionLocal() as session:
        result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
        return result.scalar() or 0
