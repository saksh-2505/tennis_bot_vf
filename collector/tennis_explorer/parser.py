from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DATE_RE = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")
RANK_RE = re.compile(r"rank\s*-\s*(\w+):\s*([\d.]+)\s*/\s*([\d.]+)")
HEIGHT_WEIGHT_RE = re.compile(r"Height\s*/\s*Weight:\s*(\d+)\s*cm\s*/\s*(\d+)\s*kg")
AGE_RE = re.compile(r"Age:\s*(\d+)")


@dataclass
class PlayerData:
    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    nationality: str | None = None
    date_of_birth: str | None = None
    age: int | None = None
    height: int | None = None
    weight: int | None = None
    plays: str | None = None
    backhand: str | None = None
    gender: str | None = None
    atp_or_wta: str | None = None
    profile_url: str | None = None

    current_rank: int | None = None
    career_high_rank: int | None = None
    ranking_points: int | None = None

    total_matches: int | None = None
    total_wins: int | None = None
    total_losses: int | None = None
    career_win_percentage: float | None = None

    hard_matches: int | None = None
    hard_wins: int | None = None
    hard_losses: int | None = None
    hard_win_percentage: float | None = None

    clay_matches: int | None = None
    clay_wins: int | None = None
    clay_losses: int | None = None
    clay_win_percentage: float | None = None

    grass_matches: int | None = None
    grass_wins: int | None = None
    grass_losses: int | None = None
    grass_win_percentage: float | None = None

    indoor_matches: int | None = None
    indoor_wins: int | None = None
    indoor_losses: int | None = None
    indoor_win_percentage: float | None = None

    first_serve_percentage: float | None = None
    first_serve_points_won: float | None = None
    second_serve_points_won: float | None = None
    service_games_won: float | None = None
    break_points_saved: float | None = None

    return_points_won: float | None = None
    return_games_won: float | None = None
    break_points_converted: float | None = None

    tie_break_record: str | None = None
    deciding_set_record: str | None = None
    retirement_record: str | None = None

    discovered_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def parse_player_profile(html: str, profile_url: str) -> PlayerData | None:
    soup = BeautifulSoup(html, "html.parser")

    full_name = _extract_full_name(soup)
    if not full_name:
        return None

    data = PlayerData(full_name=full_name, profile_url=profile_url)
    data.first_name, data.last_name = _split_name(full_name)

    _parse_profile_divs(soup, data)

    _parse_wl_table(soup, data)

    return data


def _extract_full_name(soup: BeautifulSoup) -> str | None:
    body_text = soup.get_text(strip=True)
    if "does not exist" in body_text.lower():
        return None

    h1 = soup.find("h1")
    if h1:
        text = h1.get_text(strip=True)
        text = re.sub(r"\s*-\s*profile\s*", "", text, flags=re.IGNORECASE).strip()
        if text and "does not exist" not in text.lower():
            return text.upper()

    title = soup.find("title")
    if title:
        text = title.get_text(strip=True)
        text = re.sub(r"\s*-\s*Tennis\s*Explorer\s*", "", text, flags=re.IGNORECASE).strip()
        if text and "does not exist" not in text.lower():
            return text.upper()

    return None


def _split_name(full_name: str) -> tuple[str | None, str | None]:
    parts = full_name.split()
    if len(parts) >= 2:
        return parts[1], parts[0]
    return None, parts[0] if parts else None


def _parse_profile_divs(soup: BeautifulSoup, data: PlayerData) -> None:
    root = soup.find("body") or soup.find("html") or soup
    divs = root.find_all("div")
    for div in divs:
        text = div.get_text(strip=True)
        if not text:
            continue

        if text.startswith("Country:"):
            country = text.removeprefix("Country:").strip()
            if country:
                data.nationality = country

        elif "Height" in text and "Weight" in text:
            m = HEIGHT_WEIGHT_RE.search(text)
            if m:
                data.height = int(m.group(1))
                data.weight = int(m.group(2))

        elif text.startswith("Age:"):
            m = AGE_RE.search(text)
            if m:
                data.age = int(m.group(1))
            m = DATE_RE.search(text)
            if m:
                d, mo, y = m.group(1), m.group(2), m.group(3)
                data.date_of_birth = f"{y}-{mo.zfill(2)}-{d.zfill(2)}"

        elif "rank" in text.lower() and "singles" in text.lower():
            m = RANK_RE.search(text)
            if m:
                try:
                    data.current_rank = int(float(m.group(2)))
                except ValueError:
                    pass
                try:
                    data.career_high_rank = int(float(m.group(3)))
                except ValueError:
                    pass

        elif text.startswith("Sex:"):
            gender = text.removeprefix("Sex:").strip().lower()
            data.gender = gender
            data.atp_or_wta = "ATP" if gender == "man" else "WTA"

        elif text.startswith("Plays:"):
            data.plays = text.removeprefix("Plays:").strip().lower()

        elif text.startswith("Backhand:"):
            data.backhand = text.removeprefix("Backhand:").strip().lower()


def _parse_wl_table(soup: BeautifulSoup, data: PlayerData) -> None:
    table = soup.find("table", class_="balance")
    if not table:
        return

    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if not cells:
            continue

        label = cells[0].get_text(strip=True).lower().rstrip(":")
        values = [c.get_text(strip=True) for c in cells[1:]]

        if label == "summary":
            _parse_career_wl(values, data)
            _parse_surface_wl(values, data)
        elif label.isdigit():
            pass


def _parse_career_wl(values: list[str], data: PlayerData) -> None:
    if not values:
        return

    parts = values[0].split("/")
    if len(parts) == 2:
        try:
            wins = int(parts[0])
            losses = int(parts[1])
            total = wins + losses
            pct = round(wins / total * 100, 1) if total > 0 else None

            data.total_wins = wins
            data.total_losses = losses
            data.total_matches = total
            data.career_win_percentage = pct
        except (ValueError, IndexError):
            pass


def _parse_surface_wl(values: list[str], data: PlayerData) -> None:
    surfaces = ["clay", "hard", "indoor", "grass"]
    for i, surface in enumerate(surfaces):
        if i + 1 < len(values):
            _parse_surface_row(values[i + 1], data, surface)


def _parse_surface_row(value: str, data: PlayerData, surface: str) -> None:
    if not value or value == "-":
        return

    parts = value.split("/")
    if len(parts) == 2:
        try:
            wins = int(parts[0])
            losses = int(parts[1])
            total = wins + losses
            pct = (wins / total * 100) if total > 0 else None

            setattr(data, f"{surface}_wins", wins)
            setattr(data, f"{surface}_losses", losses)
            setattr(data, f"{surface}_matches", total)
            setattr(data, f"{surface}_win_percentage", round(pct, 1) if pct is not None else None)
        except (ValueError, IndexError):
            pass
