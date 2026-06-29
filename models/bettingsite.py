"""BettingsiteFoundMatch ORM model."""
from datetime import datetime, timezone

from sqlalchemy import Float, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class BettingsiteFoundMatch(Base):
    __tablename__ = "bettingsitefoundmatches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    market_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    match_url: Mapped[str] = mapped_column(String(512), nullable=False)
    player_a: Mapped[str] = mapped_column(String(255), nullable=False)
    player_b: Mapped[str] = mapped_column(String(255), nullable=False)
    odds_player_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    odds_player_b: Mapped[float | None] = mapped_column(Float, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
