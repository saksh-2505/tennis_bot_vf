"""Live Flashscore score scraper for a single match.

Parses Flashscore mobile match page to extract set scores, current game
scores, per-set breakdown of completed game scores, and match status.

On every poll, extracts the complete game-level score history from the
detail-tab-content section, enabling reconstruction of all intermediate
game states even if previous polls missed them.
"""
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from config import settings

logger = logging.getLogger(__name__)

MOBILE_MATCH_URL = "https://www.flashscore.mobi/match/{match_id}/"

MOBILE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 14; SM-S928B) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT = 30.0

FINISHED_KEYWORDS = {"FINISHED", "RETIRED", "WALKOVER", "CANCELLED", "ABANDONED", "POSTPONED"}


@dataclass
class GameState:
    set_number: int
    game_a: int
    game_b: int


@dataclass
class ScoreSnapshot:
    set_score_a: int | None = None
    set_score_b: int | None = None
    game_score_a: int | None = None
    game_score_b: int | None = None
    point_score: str | None = None
    server: str | None = None
    is_tiebreak: bool = False
    match_finished: bool = False
    per_set_games: list[GameState] = field(default_factory=list)
    source: str = "polled"

    def content_hash(self) -> str:
        payload = json.dumps(
            {
                "sa": self.set_score_a,
                "sb": self.set_score_b,
                "ga": self.game_score_a,
                "gb": self.game_score_b,
                "pt": self.point_score,
                "sv": self.server,
                "tb": self.is_tiebreak,
                "mf": self.match_finished,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


def _detect_gaps(
    previous: str | None,
    current_a: int, current_b: int,
) -> list[tuple[int, int]]:
    """Detect and interpolate missing intermediate game score states.

    If game changes from 2-2 to 5-2, the intermediate states are
    [(3,2), (4,2)].  Returns the list of interpolated (game_a, game_b)
    tuples in chronological order, excluding the current state.
    """
    if previous is None:
        return []

    try:
        prev_a, prev_b = map(int, previous.split("-"))
    except (ValueError, AttributeError):
        return []

    diff_a = current_a - prev_a
    diff_b = current_b - prev_b

    if diff_a == 0 and diff_b == 0:
        return []
    if diff_a < 0 or diff_b < 0:
        return []

    if diff_a <= 1 and diff_b <= 1:
        return []

    interpolated: list[tuple[int, int]] = []
    for step in range(1, max(diff_a, diff_b)):
        ia = prev_a + min(step, diff_a)
        ib = prev_b + min(step, diff_b)
        if (ia, ib) != (current_a, current_b):
            interpolated.append((ia, ib))

    return interpolated


def poll_flashscore_score(tracked_match_id: int, flashscore_match_id: str) -> ScoreSnapshot:
    url = MOBILE_MATCH_URL.format(match_id=flashscore_match_id)
    try:
        with httpx.Client(
            headers=MOBILE_HEADERS, timeout=TIMEOUT, follow_redirects=True
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
            snap = _parse_live_score(resp.text)
            if snap.set_score_a is None and not snap.match_finished:
                logger.warning(
                    "Flashscore parser returned empty for %s (HTTP %d)",
                    flashscore_match_id, resp.status_code,
                )
            return snap
    except httpx.HTTPStatusError as e:
        logger.warning("Flashscore HTTP error for %s: %d", flashscore_match_id, e.response.status_code)
    except Exception as e:
        logger.debug("Flashscore poll failed for %s: %s", flashscore_match_id, e)
    return ScoreSnapshot()


def _parse_live_score(html: str) -> ScoreSnapshot:
    soup = BeautifulSoup(html, "html.parser")
    snap = ScoreSnapshot()

    details = soup.find_all("div", class_="detail")
    if not details:
        return snap

    # -- detail[0]: set score + current game scores ------------------------
    first = details[0]
    b_tag = first.find("b")
    if b_tag:
        set_text = b_tag.get_text(strip=True)
        parts = set_text.split("-")
        if len(parts) == 2:
            try:
                snap.set_score_a = int(parts[0])
                snap.set_score_b = int(parts[1])
            except ValueError:
                pass

        full_text = first.get_text(strip=True)
        game_m = re.search(r"\(([^)]+)\)", full_text)
        if game_m:
            game_pairs = game_m.group(1).split(",")
            if game_pairs:
                last_game = game_pairs[-1].strip()
                gp = last_game.split("-")
                if len(gp) == 2:
                    try:
                        snap.game_score_a = int(gp[0])
                        snap.game_score_b = int(gp[1])
                    except ValueError:
                        pass

    # -- detail[1]: match status -------------------------------------------
    if len(details) >= 2:
        status_text = details[1].get_text(strip=True).upper()
        if any(kw in status_text for kw in FINISHED_KEYWORDS):
            snap.match_finished = True

    # -- Parse per-set game scores from detail-tab-content ------------------
    tab = soup.find(id="detail-tab-content")
    if tab:
        set_games_a: list[int] = []
        set_games_b: list[int] = []
        for h4 in tab.find_all("h4"):
            text = h4.get_text(strip=True)
            set_m = re.search(
                r"Set\s+(\d+)\s*[-:]\s*(\d+)\s*[-:]\s*(\d+)",
                text, re.IGNORECASE,
            )
            if not set_m:
                set_m = re.search(
                    r"Set\s+(\d+):\s*(\d+)\s*[-:]\s*(\d+)",
                    text, re.IGNORECASE,
                )
            if set_m:
                try:
                    set_num = int(set_m.group(1))
                    ga = int(set_m.group(2))
                    gb = int(set_m.group(3))
                    set_games_a.append(ga)
                    set_games_b.append(gb)
                    snap.per_set_games.append(GameState(set_num, ga, gb))
                except ValueError:
                    pass

        if snap.set_score_a is None and set_games_a:
            wins_a = sum(1 for ga, gb in zip(set_games_a, set_games_b) if ga > gb)
            wins_b = sum(1 for ga, gb in zip(set_games_a, set_games_b) if gb > ga)
            snap.set_score_a = wins_a
            snap.set_score_b = wins_b

    return snap


def mark_match_finished(tracked_match_id: int) -> None:
    import database as db
    from sqlalchemy import text
    from models.tracked_match import TrackedMatch

    finish_utc = datetime.now(timezone.utc)

    with db.SessionLocal() as session:
        tm = session.get(TrackedMatch, tracked_match_id)
        if tm is None or tm.status == "FINISHED":
            return

        tm.status = "FINISHED"
        tm.actual_finish = finish_utc

        delta = None

        try:
            row = session.execute(text(
                "SELECT min(timestamp) FROM live_scores "
                "WHERE tracked_match_id = :mid AND timestamp IS NOT NULL",
                {"mid": tracked_match_id},
            )).fetchone()
            if row and row[0]:
                first_tick = row[0]
                if first_tick.tzinfo is None:
                    first_tick = first_tick.replace(tzinfo=timezone.utc)
                delta = finish_utc - first_tick
        except Exception:
            pass

        if delta is None or delta.total_seconds() < 0:
            start = tm.scheduled_start
            if start is not None and start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if start is not None:
                delta = finish_utc - start

        if delta is not None and delta.total_seconds() > 0 and delta.total_seconds() < 86400:
            tm.match_duration_min = int(delta.total_seconds() / 60)

        tm.updated_at = finish_utc
        session.commit()

        logger.info(
            "Match %d (%s vs %s) marked FINISHED — duration: %s min",
            tracked_match_id,
            tm.player1_name, tm.player2_name,
            tm.match_duration_min,
        )
