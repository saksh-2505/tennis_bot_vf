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


def init_db() -> None:
    """Create all tables and configure TimescaleDB hypertables.

    Safe to call at every startup — uses IF NOT EXISTS guards.
    """
    from models.completed_match import CompletedMatch
    from models.live_odds import LiveOdds
    from models.live_score import LiveScore
    from models.tracked_match import TrackedMatch

    models = [CompletedMatch, LiveScore, LiveOdds, TrackedMatch]
    for m in models:
        m.metadata.create_all(bind=engine)

    with engine.connect() as conn:
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
            "SELECT add_reorder_policy("
            "'live_scores', 'tracked_match_id',"
            " if_not_exists => TRUE"
            ")"
        ))
        conn.execute(text(
            "SELECT add_reorder_policy("
            "'live_odds', 'tracked_match_id',"
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
            "SELECT add_compression_policy("
            "'live_scores', INTERVAL '7 days',"
            " if_not_exists => TRUE"
            ")"
        ))
        conn.execute(text(
            "SELECT add_compression_policy("
            "'live_odds', INTERVAL '7 days',"
            " if_not_exists => TRUE"
            ")"
        ))
        conn.commit()

    logger.info("TimescaleDB initialized — hypertables configured, compression enabled")
