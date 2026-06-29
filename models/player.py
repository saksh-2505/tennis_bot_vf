"""Player ORM model."""
from datetime import datetime, timezone

from sqlalchemy import Float, Integer, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Player(Base):
    __tablename__ = "players"

    player_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    full_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(128), nullable=True)
    date_of_birth: Mapped[str | None] = mapped_column(String(32), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plays: Mapped[str | None] = mapped_column(String(16), nullable=True)
    backhand: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    atp_or_wta: Mapped[str | None] = mapped_column(String(8), nullable=True)
    profile_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    current_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    career_high_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ranking_points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    total_matches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_wins: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_losses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    career_win_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)

    hard_matches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hard_wins: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hard_losses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hard_win_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)

    clay_matches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clay_wins: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clay_losses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clay_win_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)

    grass_matches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grass_wins: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grass_losses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grass_win_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)

    indoor_matches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    indoor_wins: Mapped[int | None] = mapped_column(Integer, nullable=True)
    indoor_losses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    indoor_win_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)

    first_serve_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    first_serve_points_won: Mapped[float | None] = mapped_column(Float, nullable=True)
    second_serve_points_won: Mapped[float | None] = mapped_column(Float, nullable=True)
    service_games_won: Mapped[float | None] = mapped_column(Float, nullable=True)
    break_points_saved: Mapped[float | None] = mapped_column(Float, nullable=True)

    return_points_won: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_games_won: Mapped[float | None] = mapped_column(Float, nullable=True)
    break_points_converted: Mapped[float | None] = mapped_column(Float, nullable=True)

    tie_break_record: Mapped[str | None] = mapped_column(String(32), nullable=True)
    deciding_set_record: Mapped[str | None] = mapped_column(String(32), nullable=True)
    retirement_record: Mapped[str | None] = mapped_column(String(32), nullable=True)

    source: Mapped[str] = mapped_column(String(64), default="Tennis Explorer", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_updated: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
