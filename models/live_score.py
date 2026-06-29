"""LiveScore ORM model (hypertable)."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Integer, PrimaryKeyConstraint, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class LiveScore(Base):
    __tablename__ = "live_scores"

    tracked_match_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    flashscore_match_id: Mapped[str] = mapped_column(String(32), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    set_score_a: Mapped[int | None] = mapped_column(Integer, nullable=True)
    set_score_b: Mapped[int | None] = mapped_column(Integer, nullable=True)
    game_score_a: Mapped[int | None] = mapped_column(Integer, nullable=True)
    game_score_b: Mapped[int | None] = mapped_column(Integer, nullable=True)
    point_score: Mapped[str | None] = mapped_column(String(8), nullable=True)
    server: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_tiebreak: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    match_finished: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("tracked_match_id", "timestamp", "content_hash"),
    )
