"""Betting site parser: JSON response to Match objects, pipe-format odds."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from collector.flashscore.parser import Match as FlashscoreMatch

logger = logging.getLogger(__name__)

MATCH_PATTERN = " v "
EVENT_TYPE_TENNIS = 2


@dataclass
class BettingsiteMatch:
    market_id: str
    match_url: str
    player_a: str
    player_b: str
    odds_player_a: float | None
    odds_player_b: float | None
    discovered_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def filter_tennis_matches(events: list[dict]) -> list[dict]:
    return [
        e
        for e in events
        if e.get("event_type_id") == EVENT_TYPE_TENNIS
        and MATCH_PATTERN in e.get("name", "")
    ]


def match_events_to_flashscore(
    tennis_events: list[dict],
    flashscore_matches: list[FlashscoreMatch],
) -> list[tuple[dict, FlashscoreMatch]]:
    pairs: list[tuple[dict, FlashscoreMatch]] = []
    used_event_ids: set[int] = set()

    for fs_match in flashscore_matches:
        fs_last_a = _extract_last_name(fs_match.player_a)
        fs_last_b = _extract_last_name(fs_match.player_b)

        for event in tennis_events:
            if event["event_id"] in used_event_ids:
                continue

            event_name = event["name"].lower()

            if _names_match(event_name, fs_last_a, fs_last_b):
                pairs.append((event, fs_match))
                used_event_ids.add(event["event_id"])
                break

    return pairs


def parse_odds_pipe(data: str) -> dict[str, float | None]:
    if not data:
        return {}

    parts = data.split("|")
    result: dict[str, float | None] = {}

    idx = 1
    while idx < len(parts) - 3:
        if parts[idx] == "OPEN" or parts[idx] == "SUSPENDED":
            idx += 1
            continue
        if parts[idx] == "0":
            idx += 1
            continue
        if not parts[idx].replace(".", "").isdigit():
            idx += 1
            continue

        idx += 1

        selection_id = ""
        while idx < len(parts):
            if parts[idx] in ("ACTIVE", "SUSPENDED", "REMOVED", "LOSER", "WINNER"):
                status = parts[idx]
                idx += 1
                break
            if parts[idx].isdigit() and len(parts[idx]) >= 6:
                selection_id = parts[idx]
                idx += 1
                if idx < len(parts) and parts[idx] in (
                    "ACTIVE", "SUSPENDED", "REMOVED", "LOSER", "WINNER"
                ):
                    status = parts[idx]
                    idx += 1
                    break
            idx += 1
        else:
            break

        if not selection_id or status != "ACTIVE":
            continue

        if idx < len(parts):
            try:
                back_odds = float(parts[idx])
                result[selection_id] = back_odds
            except (ValueError, IndexError):
                result[selection_id] = None
            idx += 1

    return result


def parse_odds_for_runners(
    pipe_data: str | None,
    runner_a_id: str,
    runner_b_id: str,
) -> tuple[float | None, float | None]:
    if not pipe_data:
        return None, None

    odds_map = parse_odds_pipe(pipe_data)
    return odds_map.get(runner_a_id), odds_map.get(runner_b_id)


def _extract_last_name(full_name: str) -> str:
    name = full_name.strip().lower()
    parts = name.split()
    if len(parts) <= 1:
        return name
    if len(parts) == 2:
        return parts[-1]
    if len(parts) >= 3:
        last_two = f"{parts[-2]} {parts[-1]}"
        return last_two
    return parts[-1]


def _names_match(event_name: str, last_a: str, last_b: str) -> bool:
    words_a = last_a.split()
    words_b = last_b.split()

    a_match = all(_word_matches(w, event_name) for w in words_a)
    b_match = all(_word_matches(w, event_name) for w in words_b)

    return a_match and b_match


def _word_matches(word: str, event_name: str) -> bool:
    if word in event_name:
        return True
    if len(word) >= 5:
        prefix = word[:5]
        return prefix in event_name
    return False
