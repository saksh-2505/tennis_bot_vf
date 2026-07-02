"""SystemEvent ORM model (hypertable) — structured event log."""
import secrets
from datetime import datetime, timezone

from sqlalchemy import Integer, PrimaryKeyConstraint, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


def _default_id() -> str:
    return secrets.token_hex(16)


class SystemEvent(Base):
    __tablename__ = "system_events"

    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    event_id: Mapped[str] = mapped_column(String(32), nullable=False, default=_default_id)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    incident_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tracked_match_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint("timestamp", "event_id"),
    )
