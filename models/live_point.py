"""LivePoint ORM model (hypertable) — individual tennis points."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Float, Integer, PrimaryKeyConstraint, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class LivePoint(Base):
    __tablename__ = "live_points"

    tracked_match_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    flashscore_match_id: Mapped[str] = mapped_column(String(32), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    set_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    game_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    point_a: Mapped[int | None] = mapped_column(Integer, nullable=True)
    point_b: Mapped[int | None] = mapped_column(Integer, nullable=True)
    point_string: Mapped[str | None] = mapped_column(String(16), nullable=True)
    server_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_break_point: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_set_point: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_match_point: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_tiebreak: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("tracked_match_id", "timestamp", "content_hash"),
    )
