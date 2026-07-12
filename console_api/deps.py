"""Dependencies: database session, settings, pagination helpers."""
from __future__ import annotations

import os
from typing import Generator

from fastapi import Query
from sqlalchemy.orm import Session

from config import settings as app_settings
from database import SessionLocal


def get_settings():
    return app_settings


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
) -> dict:
    return {"page": page, "page_size": page_size, "offset": (page - 1) * page_size}


def time_range_params(
    from_ts: str | None = Query(None, description="ISO 8601 start timestamp"),
    to_ts: str | None = Query(None, description="ISO 8601 end timestamp"),
) -> dict:
    return {"from_ts": from_ts, "to_ts": to_ts}
