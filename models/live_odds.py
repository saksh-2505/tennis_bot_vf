"""LiveOdds ORM model (hypertable)."""
from datetime import datetime, timezone

from sqlalchemy import Float, Integer, PrimaryKeyConstraint, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class LiveOdds(Base):
    __tablename__ = "live_odds"

    tracked_match_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    betting_market_id: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    back_odds_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    back_odds_b: Mapped[float | None] = mapped_column(Float, nullable=True)
    lay_odds_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    lay_odds_b: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_b: Mapped[float | None] = mapped_column(Float, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("tracked_match_id", "timestamp", "content_hash"),
    )
