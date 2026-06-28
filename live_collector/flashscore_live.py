import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup, Tag

from config import settings

logger = logging.getLogger(__name__)

MATCH_URL = "https://www.flashscore.com/match/{match_id}/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT = 30.0


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
    """Fetch the Flas hscore match page and extract the current score state."""
    url = MATCH_URL.format(match_id=flashscore_match_id)
    try:
        with httpx.Client(
            headers=HEADERS, timeout=TIMEOUT, follow_redirects=True
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return _parse_live_score(resp.text)
    except Exception:
        logger.debug("Flashscore poll failed for match %s", flashscore_match_id)
        return ScoreSnapshot()


def _parse_live_score(html: str) -> ScoreSnapshot:
    soup = BeautifulSoup(html, "html.parser")
    snap = ScoreSnapshot()

    # -- detect finished --------------------------------------------------
    detail = soup.find("div", class_="detailScore")
    if detail:
        status_elem = detail.find(
            "div", class_=re.compile(r"status|matchStatus", re.I)
        )
        if status_elem:
            text = status_elem.get_text(strip=True).upper()
            if "FINISHED" in text or "RETIRED" in text:
                snap.match_finished = True

    if not snap.match_finished:
        all_text = soup.get_text()
        if "Match Finished" in all_text or "RETIRED" in all_text:
            snap.match_finished = True

    if snap.match_finished:
        return snap

    # -- set scores -------------------------------------------------------
    set_divs = soup.find_all(
        "div", class_=re.compile(r"set.*score|score.*set", re.I)
    )
    sets_a: list[int] = []
    sets_b: list[int] = []
    for sd in set_divs:
        vals = [t.strip() for t in sd.get_text(separator=" ", strip=True).split() if t.strip().isdigit()]
        if vals:
            vals = vals[-2:]
        if len(vals) >= 2:
            try:
                sets_a.append(int(vals[-2]))
                sets_b.append(int(vals[-1]))
            except ValueError:
                continue

    if sets_a:
        snap.set_score_a = len([s for s, _ in zip(sets_a, sets_b) if s is not None])
        snap.set_score_b = len([s for _, s in zip(sets_a, sets_b) if s is not None])

    current_set_idx = len(sets_a)

    # -- game scores -------------------------------------------------------
    game_blocks = soup.find_all(
        "div", class_=re.compile(r"game.*score|score.*game", re.I)
    )
    if not game_blocks:
        snap.game_score_a = 0
        snap.game_score_b = 0

    # -- point score --------------------------------------------------------
    point_el = soup.find(
        "span", class_=re.compile(r"point|scoreboard", re.I)
    )
    if point_el:
        pt = point_el.get_text(strip=True)
        snap.point_score = pt if pt else None

    # -- server -------------------------------------------------------------
    serve_el = soup.find(
        "span", class_=re.compile(r"serve|server", re.I)
    )
    if serve_el:
        snap.server = serve_el.get_text(strip=True)

    # -- title text for set/game fallback -----------------------------------
    title = soup.find("title")
    title_text = title.get_text() if title else ""
    m = re.search(r"(\d+)\s*-\s*(\d+)", title_text)
    if m and snap.set_score_a is None:
        snap.set_score_a = int(m.group(1))
        snap.set_score_b = int(m.group(2))

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
