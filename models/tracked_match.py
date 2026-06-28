from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class TrackedMatch(Base):
    __tablename__ = "tracked_matches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    flashscore_match_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    betting_market_id: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    player1_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player2_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player1_name: Mapped[str] = mapped_column(String(255), nullable=False)
    player2_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tournament: Mapped[str] = mapped_column(String(255), nullable=False)
    round: Mapped[str | None] = mapped_column(String(100), nullable=True)
    surface: Mapped[str | None] = mapped_column(String(50), nullable=True)
    scheduled_start: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    actual_finish: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    match_duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    live_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DISCOVERED")
    tracking_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
