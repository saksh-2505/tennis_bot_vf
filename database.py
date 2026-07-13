"""SQLAlchemy engine, SessionLocal, Base, init_db()."""
import logging
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _run_migrations(conn):
    """Add new columns to existing tables (idempotent via IF NOT EXISTS)."""
    migrations = [
        "ALTER TABLE completed_matches ADD COLUMN IF NOT EXISTS expected_score_states INTEGER",
        "ALTER TABLE completed_matches ADD COLUMN IF NOT EXISTS unique_score_states INTEGER",
        "ALTER TABLE completed_matches ADD COLUMN IF NOT EXISTS odds_at_score_pct DOUBLE PRECISION",
        "ALTER TABLE completed_matches ADD COLUMN IF NOT EXISTS score_completeness_pct DOUBLE PRECISION",
        "ALTER TABLE completed_matches ADD COLUMN IF NOT EXISTS odds_completeness_pct DOUBLE PRECISION",
        "ALTER TABLE completed_matches ADD COLUMN IF NOT EXISTS timeline_completeness_pct DOUBLE PRECISION",
        "ALTER TABLE completed_matches ADD COLUMN IF NOT EXISTS synchronization_score DOUBLE PRECISION",
        "ALTER TABLE completed_matches ADD COLUMN IF NOT EXISTS quality_grade VARCHAR(2)",
        "ALTER TABLE completed_matches ADD COLUMN IF NOT EXISTS quality_score DOUBLE PRECISION",
        "ALTER TABLE completed_matches ADD COLUMN IF NOT EXISTS failure_category VARCHAR(64)",
        "ALTER TABLE completed_matches ADD COLUMN IF NOT EXISTS failure_reason VARCHAR(1024)",
        "ALTER TABLE completed_matches ADD COLUMN IF NOT EXISTS market_assigned_at TIMESTAMPTZ",
        "ALTER TABLE completed_matches ADD COLUMN IF NOT EXISTS collector_started_at TIMESTAMPTZ",
        "ALTER TABLE completed_matches ADD COLUMN IF NOT EXISTS collector_finished_at TIMESTAMPTZ",
        "ALTER TABLE completed_matches ADD COLUMN IF NOT EXISTS repair_actions VARCHAR(1024)",
        "ALTER TABLE completed_matches ADD COLUMN IF NOT EXISTS repair_count INTEGER DEFAULT 0",
        "ALTER TABLE completed_matches ADD COLUMN IF NOT EXISTS last_repaired_at TIMESTAMPTZ",
        "ALTER TABLE tracked_matches ADD COLUMN IF NOT EXISTS market_assigned_at TIMESTAMPTZ",
        "ALTER TABLE tracked_matches ADD COLUMN IF NOT EXISTS collection_started_at TIMESTAMPTZ",
        "ALTER TABLE live_scores ADD COLUMN IF NOT EXISTS source VARCHAR(16) DEFAULT 'polled'",
    ]
    for sql in migrations:
        try:
            conn.execute(text(sql))
        except Exception as e:
            logger.debug("Migration skipped: %s", e)


def init_db() -> None:
    """Create all tables and configure TimescaleDB hypertables.

    Safe to call at every startup — uses IF NOT EXISTS guards.
    """
    from models.completed_match import CompletedMatch
    from models.live_odds import LiveOdds
    from models.live_point import LivePoint
    from models.live_score import LiveScore
    from models.system_event import SystemEvent
    from models.tracked_match import TrackedMatch
    from matcher.models import MatchAttempt

    models = [CompletedMatch, LiveScore, LiveOdds, LivePoint, SystemEvent, TrackedMatch, MatchAttempt]
    for m in models:
        m.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        _run_migrations(conn)
        conn.execute(text(
            "SELECT create_hypertable("
            "'live_scores', 'timestamp',"
            " chunk_time_interval => INTERVAL '1 day',"
            " if_not_exists => TRUE"
            ")"
        ))
        conn.execute(text(
            "SELECT create_hypertable("
            "'live_odds', 'timestamp',"
            " chunk_time_interval => INTERVAL '1 day',"
            " if_not_exists => TRUE"
            ")"
        ))
        conn.execute(text(
            "SELECT create_hypertable("
            "'system_events', 'timestamp',"
            " chunk_time_interval => INTERVAL '1 day',"
            " if_not_exists => TRUE"
            ")"
        ))
        conn.execute(text(
            "SELECT create_hypertable("
            "'live_points', 'timestamp',"
            " chunk_time_interval => INTERVAL '1 day',"
            " if_not_exists => TRUE"
            ")"
        ))
        conn.execute(text(
            "ALTER TABLE live_scores SET ("
            "  timescaledb.compress,"
            "  timescaledb.compress_segmentby = 'tracked_match_id'"
            ")"
        ))
        conn.execute(text(
            "ALTER TABLE live_odds SET ("
            "  timescaledb.compress,"
            "  timescaledb.compress_segmentby = 'tracked_match_id'"
            ")"
        ))
        conn.execute(text(
            "ALTER TABLE system_events SET ("
            "  timescaledb.compress"
            ")"
        ))
        conn.execute(text(
            "ALTER TABLE live_points SET ("
            "  timescaledb.compress,"
            "  timescaledb.compress_segmentby = 'tracked_match_id'"
            ")"
        ))
        conn.commit()

        for tbl in ("live_scores", "live_odds", "system_events", "live_points"):
            try:
                conn.execute(text(
                    f"SELECT add_compression_policy("
                    f"'{tbl}', INTERVAL '7 days',"
                    f" if_not_exists => TRUE)"
                ))
                conn.execute(text(
                    f"SELECT add_reorder_policy("
                    f"'{tbl}', 'tracked_match_id',"
                    f" if_not_exists => TRUE)"
                ))
                # Drop chunks older than 90 days to prevent unbounded growth
                conn.execute(text(
                    f"SELECT add_retention_policy("
                    f"'{tbl}', INTERVAL '90 days',"
                    f" if_not_exists => TRUE)"
                ))
            except Exception:
                logger.warning("Could not add policy for %s — skipping", tbl)
        conn.commit()

    logger.info("TimescaleDB initialized — hypertables configured, compression enabled")
