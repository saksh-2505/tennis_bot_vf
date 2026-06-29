"""CompletedMatch ORM model."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class CompletedMatch(Base):
    __tablename__ = "completed_matches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tracked_match_id: Mapped[int] = mapped_column(
        Integer, unique=True, nullable=False, index=True
    )
    flashscore_match_id: Mapped[str] = mapped_column(String(32), nullable=False)
    betting_market_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    player1_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player2_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    tournament: Mapped[str] = mapped_column(String(255), nullable=False)
    round: Mapped[str | None] = mapped_column(String(100), nullable=True)
    surface: Mapped[str | None] = mapped_column(String(50), nullable=True)

    scheduled_start: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    actual_finish: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    winner_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_set_score: Mapped[str | None] = mapped_column(String(20), nullable=True)
    total_sets: Mapped[int | None] = mapped_column(Integer, nullable=True)

    score_tick_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    odds_tick_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    first_score_timestamp: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_score_timestamp: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    first_odds_timestamp: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_odds_timestamp: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    score_collection_duration_seconds: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    odds_collection_duration_seconds: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    duplicate_score_ticks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_odds_ticks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    largest_score_gap_seconds: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    largest_odds_gap_seconds: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    has_complete_score_data: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    has_complete_odds_data: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    ready_for_replay: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    ready_for_feature_extraction: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    ready_for_backtesting: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    validation_passed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    exported: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    finalized_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    collector_version: Mapped[str] = mapped_column(
        String(32), default="3.0.0", nullable=False
    )
