from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Incident(Base):
    __tablename__ = "incidents"

    incident_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="WARNING")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="Unknown")
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    tracked_match_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    collector_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    incident_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    first_detected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_detected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    recovery_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

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
