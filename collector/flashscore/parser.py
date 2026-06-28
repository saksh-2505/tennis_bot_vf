from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone

from bs4 import BeautifulSoup, NavigableString, Tag

logger = logging.getLogger(__name__)

SINGLES_TOURNAMENT_PREFIXES = (
    "ATP - SINGLES:",
    "WTA - SINGLES:",
    "CHALLENGER MEN - SINGLES:",
    "CHALLENGER WOMEN - SINGLES:",
)

STATUS_SCHEDULED = "SCHEDULED"
STATUS_LIVE = "LIVE"
STATUS_FINISHED = "FINISHED"


@dataclass
class RawMatch:
    flashscore_match_id: str
    tournament: str
    player_a_abbr: str
    player_b_abbr: str
    scheduled_time_str: str
    status: str


@dataclass
class Match:
    flashscore_match_id: str
    tournament: str
    player_a: str
    player_b: str
    scheduled_start_time: datetime | None
    status: str
    discovered_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def parse_mobile_listing(html: str) -> list[RawMatch]:
    soup = BeautifulSoup(html, "html.parser")
    score_div = soup.find("div", id="score-data")
    if score_div is None:
        logger.warning("No #score-data div found in mobile listing page")
        return []

    raw_matches: list[RawMatch] = []
    current_tournament: str | None = None
    pending_time_span: str = ""

    for child in score_div.children:
        if isinstance(child, Tag) and child.name == "h4":
            current_tournament = child.get_text(strip=True)
            pending_time_span = ""
            continue

        if isinstance(child, Tag) and child.name == "span":
            pending_time_span = child.get_text(strip=True)
            continue

        if (
            isinstance(child, Tag)
            and child.name == "a"
            and child.get("href", "").startswith("/match/")
        ):
            match_id = _extract_match_id(child["href"])
            status = _determine_status(
                child.get("class", []),
                child.get_text(strip=True),
            )

            players_text = _collect_players_text(child)
            player_a, player_b = _split_players(players_text)

            if not player_a or not player_b or not match_id:
                pending_time_span = ""
                continue

            raw_matches.append(
                RawMatch(
                    flashscore_match_id=match_id,
                    tournament=current_tournament or "",
                    player_a_abbr=player_a,
                    player_b_abbr=player_b,
                    scheduled_time_str=pending_time_span,
                    status=status,
                )
            )
            pending_time_span = ""

    return raw_matches


def filter_singles(raw_matches: list[RawMatch]) -> list[RawMatch]:
    return [
        m
        for m in raw_matches
        if m.tournament.upper().startswith(SINGLES_TOURNAMENT_PREFIXES)
    ]


def extract_full_names_from_title(html: str) -> tuple[str, str] | None:
    match = re.search(r"<title>([^<]+)</title>", html)
    if not match:
        return None
    title = match.group(1)

    title = re.sub(r"\s+LIVE\s+", " ", title)
    title = re.sub(r"\s*\|\s*Tennis\s*[-–]\s*Flashscore\s*$", "", title).strip()

    for sep in (" v ", " - "):
        if sep in title:
            parts = title.split(sep, 1)
            if len(parts) == 2:
                player_a = _clean_name(parts[0].strip())
                player_b = _clean_name(parts[1].strip())
                if player_a and player_b:
                    return player_a, player_b

    return None


def extract_match_date_from_title(html: str) -> date | None:
    match = re.search(r"<title>([^<]+)</title>", html)
    if not match:
        return None
    title = match.group(1)

    date_match = re.search(r"(\d{2})/(\d{2})/(\d{4})", title)
    if date_match:
        try:
            return date(
                int(date_match.group(3)),
                int(date_match.group(2)),
                int(date_match.group(1)),
            )
        except ValueError:
            return None
    return None


def build_match(
    raw: RawMatch,
    full_names: tuple[str, str] | None = None,
    match_date: date | None = None,
) -> Match:
    if full_names:
        player_a, player_b = full_names
    else:
        player_a = _expand_abbreviated_name(raw.player_a_abbr)
        player_b = _expand_abbreviated_name(raw.player_b_abbr)

    player_a = _normalize_name(player_a)
    player_b = _normalize_name(player_b)

    scheduled = _parse_time(raw.scheduled_time_str, match_date)

    return Match(
        flashscore_match_id=raw.flashscore_match_id,
        tournament=raw.tournament,
        player_a=player_a,
        player_b=player_b,
        scheduled_start_time=scheduled,
        status=raw.status,
    )


def _extract_match_id(href: str) -> str:
    parts = href.strip("/").split("/")
    if len(parts) >= 2 and parts[-2] == "match":
        return parts[-1]
    return ""


def _determine_status(classes: list[str], link_text: str) -> str:
    class_str = " ".join(classes).lower()
    link_text_upper = link_text.upper()

    if "live" in class_str:
        return STATUS_LIVE
    if "fin" in class_str:
        if "RETIRED" in link_text_upper:
            return "RETIRED"
        if "WO" in link_text_upper or "WALKOVER" in link_text_upper:
            return "WALKOVER"
        return STATUS_FINISHED
    return STATUS_SCHEDULED


def _collect_players_text(link_tag: Tag) -> str:
    parts: list[str] = []
    for sibling in link_tag.previous_siblings:
        if isinstance(sibling, Tag):
            if sibling.name == "h4":
                break
            if sibling.name == "span":
                break
            continue
        if isinstance(sibling, NavigableString):
            text = sibling.string.strip()
            if text:
                parts.insert(0, text)
    return " ".join(parts).strip()


def _split_players(text: str) -> tuple[str, str]:
    text = re.sub(r"\s+", " ", text).strip()
    for sep in (" - ", " – "):
        if sep in text:
            player_a, player_b = text.split(sep, 1)
            return player_a.strip().rstrip("."), player_b.strip().rstrip(".")
    return "", ""


def _clean_name(name: str) -> str:
    name = re.sub(r"\s*\d{2}/\d{2}/\d{4}.*$", "", name)
    name = re.sub(r"\s*\d{1,2}:\d{2}.*$", "", name)
    name = re.sub(r"\s*LIVE\s*$", "", name)
    return name.strip()


def _normalize_name(name: str) -> str:
    name = re.sub(r"\s*\([^)]*\)", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name.upper()


def _expand_abbreviated_name(abbr: str) -> str:
    abbr = re.sub(r"\s*\([^)]*\)", "", abbr).strip()
    if "/" in abbr:
        return abbr
    if "." in abbr:
        return abbr.replace(".", "").upper()
    return abbr


def _parse_time(time_str: str, match_date: date | None = None) -> datetime | None:
    if not time_str:
        return None
    time_str = re.sub(r"\s+", " ", time_str).strip()
    m = re.match(r"^(\d{1,2}):(\d{2})$", time_str)
    if not m:
        return None
    try:
        t = time(int(m.group(1)), int(m.group(2)))
    except ValueError:
        return None
    d = match_date or date.today()
    return datetime.combine(d, t)
