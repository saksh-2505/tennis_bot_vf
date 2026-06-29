"""Live Flashscore score scraper for a single match."""
import hashlib
import json
import logging
import re
from dataclasses import dataclass
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
class ScoreSnapshot:
    set_score_a: int | None = None
    set_score_b: int | None = None
    game_score_a: int | None = None
    game_score_b: int | None = None
    point_score: str | None = None
    server: str | None = None
    is_tiebreak: bool = False
    match_finished: bool = False

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


def poll_flashscore_score(match_id: str, flashscore_match_id: str) -> ScoreSnapshot:
    """Fetch the Flashscore mobile match page and extract the current score state."""
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
    """Parse Flashscore mobile match page into ScoreSnapshot.

    Flashscore.mobi returns static HTML with scores directly embedded.
    The structure for a match page is:

        <h3>Player1 (Ctry) - Player2 (Ctry)</h3>
        <div class="detail"><b>2-1</b>  (6-7,7-5,6-3)</div>
        <div class="detail">Finished</div>  ← or live status
        <div class="detail">28.06.2026 18:30</div>

    For live in-progress matches the format is the same but without
    ``Finished`` and set/game scores reflect current state.
    """
    soup = BeautifulSoup(html, "html.parser")
    snap = ScoreSnapshot()

    details = soup.find_all("div", class_="detail")
    if not details:
        return snap

    # -- detail[0]: set score + game scores -------------------------------
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

        # Game scores follow the <b> tag in parentheses
        # e.g. (6-7,7-5,6-3)
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

    # -- detail[1]: match status ------------------------------------------
    if len(details) >= 2:
        status_text = details[1].get_text(strip=True).upper()
        if any(kw in status_text for kw in FINISHED_KEYWORDS):
            snap.match_finished = True
        elif "LIVE" in status_text or "IN PLAY" in status_text:
            pass  # match is live, keep going

    # -- detail[2]: date/time (not used currently) ------------------------

    # -- point score from title if available -----------------------------
    title = soup.find("title")
    if title:
        title_text = title.get_text(strip=True)
        pt_m = re.search(r"(\d+)\s*[-:]\s*(\d+)(?:\s|$)", title_text)
        if pt_m and snap.game_score_a is None and snap.game_score_b is None:
            try:
                snap.game_score_a = int(pt_m.group(1))
                snap.game_score_b = int(pt_m.group(2))
            except ValueError:
                pass

    # -- Parse per-set game scores from detail-tab-content ----------------
    tab = soup.find(id="detail-tab-content")
    if tab:
        set_games_a: list[int] = []
        set_games_b: list[int] = []
        for h4 in tab.find_all("h4"):
            text = h4.get_text(strip=True)
            set_m = re.search(r"Set\s+\d+:\s*(\d+)\s*[-:]\s*(\d+)", text, re.IGNORECASE)
            if set_m:
                try:
                    set_games_a.append(int(set_m.group(1)))
                    set_games_b.append(int(set_m.group(2)))
                except ValueError:
                    pass

        # Only set set_score from detail-tab-content if <b> tag parsing
        # failed (it's more reliable when available)
        if snap.set_score_a is None and set_games_a:
            wins_a = sum(1 for ga, gb in zip(set_games_a, set_games_b) if ga > gb)
            wins_b = sum(1 for ga, gb in zip(set_games_a, set_games_b) if gb > ga)
            snap.set_score_a = wins_a
            snap.set_score_b = wins_b

        # Use game scores from the last completed set as current game score
        if snap.game_score_a is None and set_games_a:
            snap.game_score_a = set_games_a[-1]
            snap.game_score_b = set_games_b[-1]

    return snap


def mark_match_finished(tracked_match_id: int) -> None:
    """Update tracked_matches with FINISHED status and calculate duration."""
    import database as db
    from models.tracked_match import TrackedMatch

    finish_utc = datetime.now(timezone.utc)

    with db.SessionLocal() as session:
        tm = session.get(TrackedMatch, tracked_match_id)
        if tm is None or tm.status == "FINISHED":
            return

        tm.status = "FINISHED"
        tm.actual_finish = finish_utc
        if tm.scheduled_start is not None:
            sched = tm.scheduled_start
            if sched.tzinfo is None:
                sched = sched.replace(tzinfo=timezone.utc)
            delta = finish_utc - sched
            tm.match_duration_min = int(delta.total_seconds() / 60)
        tm.updated_at = finish_utc
        session.commit()

        logger.info(
            "Match %d (%s vs %s) marked FINISHED — duration: %s min",
            tracked_match_id,
            tm.player1_name, tm.player2_name,
            tm.match_duration_min,
        )
