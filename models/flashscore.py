from datetime import datetime, timezone

from sqlalchemy import Float, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class FlashscoreFoundMatch(Base):
    __tablename__ = "flashscorefoundmatches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    flashscore_match_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    tournament: Mapped[str] = mapped_column(String(255), nullable=False)
    player_a: Mapped[str] = mapped_column(String(255), nullable=False)
    player_b: Mapped[str] = mapped_column(String(255), nullable=False)
    scheduled_start_time: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
