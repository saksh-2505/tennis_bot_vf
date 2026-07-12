"""MatchAttempt ORM model — persistent log of every matching attempt."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class MatchAttempt(Base):
    __tablename__ = "match_attempts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    flashscore_match_id: Mapped[str] = mapped_column(
        String(32), index=True, nullable=False,
    )
    betting_market_id: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False,
    )
    player1_name: Mapped[str] = mapped_column(String(255), nullable=False)
    player2_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tournament: Mapped[str] = mapped_column(String(255), nullable=False)

    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_level: Mapped[str] = mapped_column(
        String(16), nullable=False,
    )
    signal_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    signal_reasons: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rejected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
