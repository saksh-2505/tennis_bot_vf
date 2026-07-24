from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from console_api.deps import get_db

router = APIRouter()


@router.get("/db/tables")
def db_tables(db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            "SELECT schemaname, tablename, n_live_tup "
            "FROM pg_stat_user_tables "
            "ORDER BY schemaname, tablename"
        )
    ).fetchall()

    return {
        "tables": [
            {
                "schema": r[0],
                "table": r[1],
                "row_count": r[2] or 0,
            }
            for r in rows
        ],
    }


@router.get("/db/table/{table_name}")
def db_table_data(
    table_name: str,
    db: Session = Depends(get_db),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    ALLOWED_TABLES = {
        "tracked_matches", "completed_matches", "players",
        "flashscorefoundmatches", "bettingsitefoundmatches",
        "live_scores", "live_odds", "system_events",
        "match_attempts", "incidents",
    }

    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=403, detail="Table not allowed")

    rows = db.execute(
        text(f"SELECT * FROM {table_name} ORDER BY 1 DESC OFFSET :offset LIMIT :limit"),
        {"offset": offset, "limit": limit},
    ).fetchall()

    columns = list(rows[0]._mapping.keys()) if rows else []

    return {
        "table": table_name,
        "columns": columns,
        "offset": offset,
        "limit": limit,
        "rows": [
            {k: _serialize(v) for k, v in dict(r._mapping).items()}
            for r in rows
        ],
    }


def _serialize(v):
    from datetime import datetime
    from decimal import Decimal
    try:
        from uuid import UUID
    except ImportError:  # pragma: no cover
        UUID = None

    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, Decimal):
        # `numeric` columns (e.g. live_odds volumes) arrive as Decimal — encode as float.
        return float(v)
    if UUID is not None and isinstance(v, UUID):
        return str(v)
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf-8", errors="replace")
    if isinstance(v, dict):
        return {k: _serialize(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [_serialize(val) for val in v]
    return v
