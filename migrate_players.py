"""One-time migration: copy 20 players from SQLite → PostgreSQL.

Usage:
    python migrate_players.py

Requires both SQLite database (trading.db) and a running PostgreSQL
instance (docker compose up).  Reads all rows from the SQLite ``players``
table and writes them to the PostgreSQL table.

All other tables (flashscorefoundmatches, bettingsitefoundmatches,
tracked_matches) are intentionally NOT migrated — they will be
re-populated by the first discovery cycle.
"""

import logging
import sys
from datetime import datetime, timezone

from config import settings
from database import Base, SessionLocal, engine

logger = logging.getLogger(__name__)


def migrate():
    import sqlite3

    sqlite_path = "trading.db"

    try:
        sqlite_conn = sqlite3.connect(sqlite_path)
    except Exception as e:
        logger.error("Cannot open SQLite DB at %s: %s", sqlite_path, e)
        sys.exit(1)

    # ---- read from SQLite -----------------------------------------------
    rows = sqlite_conn.execute("SELECT * FROM players").fetchall()
    cols = [d[0] for d in sqlite_conn.execute("PRAGMA table_info(players)")]

    if not rows:
        logger.info("No players found in SQLite — nothing to migrate")
        sqlite_conn.close()
        return

    # ---- create table in PostgreSQL --------------------------------------
    from models.player import Player

    Player.metadata.create_all(bind=engine)

    # ---- convert and write -----------------------------------------------
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        existing = {p.full_name for p in session.query(Player.full_name).all()}
        inserted = 0
        skipped = 0

        for row in rows:
            record = dict(zip(cols, row))
            full_name = record["full_name"]
            if full_name in existing:
                skipped += 1
                continue

            for col in cols:
                val = record[col]
                if col.endswith("_at") and isinstance(val, str):
                    try:
                        dt = datetime.fromisoformat(val)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        record[col] = dt
                    except (ValueError, TypeError):
                        record[col] = None

            player = Player(**{k: v for k, v in record.items() if k != "player_id"})
            session.add(player)
            inserted += 1

        session.commit()

    sqlite_conn.close()
    logger.info(
        "Migration complete: %d players inserted, %d skipped (already present)",
        inserted, skipped,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
    migrate()
