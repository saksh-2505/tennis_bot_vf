"""Tennis Explorer player profile fetcher and DB upsert."""
import logging

from database import SessionLocal, engine
from models.player import Player

from .client import fetch_player_profile, search_player
from .parser import PlayerData, parse_player_profile

logger = logging.getLogger(__name__)


def update_player(player_name: str) -> bool:
    logger.info("Searching Tennis Explorer for: %s", player_name)

    result = search_player(player_name)
    if not result:
        logger.warning("No Tennis Explorer profile found for: %s", player_name)
        return False

    url_path = result["url"]
    profile_url = f"https://www.tennisexplorer.com/player/{url_path}/"

    html = fetch_player_profile(url_path)
    data = parse_player_profile(html, profile_url)
    if not data:
        logger.warning("Failed to parse profile for: %s", player_name)
        return False

    _upsert_player(data)
    logger.info("Updated player: %s", data.full_name)
    return True


def update_players(player_names: list[str]) -> dict[str, bool]:
    results: dict[str, bool] = {}
    for name in player_names:
        try:
            results[name] = update_player(name)
        except Exception:
            logger.exception("Failed to update player: %s", name)
            results[name] = False
    return results


def _upsert_player(data: PlayerData) -> None:
    Player.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        existing = (
            session.query(Player).filter_by(full_name=data.full_name).first()
        )

        if existing:
            _update_existing(existing, data)
        else:
            record = _build_record(data)
            session.add(record)

        session.commit()


def _update_existing(player: Player, data: PlayerData) -> None:
    fields = [
        "first_name",
        "last_name",
        "nationality",
        "date_of_birth",
        "age",
        "height",
        "weight",
        "plays",
        "backhand",
        "gender",
        "atp_or_wta",
        "profile_url",
        "current_rank",
        "career_high_rank",
        "ranking_points",
        "total_matches",
        "total_wins",
        "total_losses",
        "career_win_percentage",
        "hard_matches",
        "hard_wins",
        "hard_losses",
        "hard_win_percentage",
        "clay_matches",
        "clay_wins",
        "clay_losses",
        "clay_win_percentage",
        "grass_matches",
        "grass_wins",
        "grass_losses",
        "grass_win_percentage",
        "indoor_matches",
        "indoor_wins",
        "indoor_losses",
        "indoor_win_percentage",
        "first_serve_percentage",
        "first_serve_points_won",
        "second_serve_points_won",
        "service_games_won",
        "break_points_saved",
        "return_points_won",
        "return_games_won",
        "break_points_converted",
        "tie_break_record",
        "deciding_set_record",
        "retirement_record",
    ]

    for field_name in fields:
        value = getattr(data, field_name)
        if value is not None:
            setattr(player, field_name, value)


def _build_record(data: PlayerData) -> Player:
    return Player(
        full_name=data.full_name,
        first_name=data.first_name,
        last_name=data.last_name,
        nationality=data.nationality,
        date_of_birth=data.date_of_birth,
        age=data.age,
        height=data.height,
        weight=data.weight,
        plays=data.plays,
        backhand=data.backhand,
        gender=data.gender,
        atp_or_wta=data.atp_or_wta,
        profile_url=data.profile_url,
        current_rank=data.current_rank,
        career_high_rank=data.career_high_rank,
        ranking_points=data.ranking_points,
        total_matches=data.total_matches,
        total_wins=data.total_wins,
        total_losses=data.total_losses,
        career_win_percentage=data.career_win_percentage,
        hard_matches=data.hard_matches,
        hard_wins=data.hard_wins,
        hard_losses=data.hard_losses,
        hard_win_percentage=data.hard_win_percentage,
        clay_matches=data.clay_matches,
        clay_wins=data.clay_wins,
        clay_losses=data.clay_losses,
        clay_win_percentage=data.clay_win_percentage,
        grass_matches=data.grass_matches,
        grass_wins=data.grass_wins,
        grass_losses=data.grass_losses,
        grass_win_percentage=data.grass_win_percentage,
        indoor_matches=data.indoor_matches,
        indoor_wins=data.indoor_wins,
        indoor_losses=data.indoor_losses,
        indoor_win_percentage=data.indoor_win_percentage,
        first_serve_percentage=data.first_serve_percentage,
        first_serve_points_won=data.first_serve_points_won,
        second_serve_points_won=data.second_serve_points_won,
        service_games_won=data.service_games_won,
        break_points_saved=data.break_points_saved,
        return_points_won=data.return_points_won,
        return_games_won=data.return_games_won,
        break_points_converted=data.break_points_converted,
        tie_break_record=data.tie_break_record,
        deciding_set_record=data.deciding_set_record,
        retirement_record=data.retirement_record,
    )
