"""Live tennis point collector — parses Flashscore JSON feed for point-by-point data.

Flashscore provides a JSON feed endpoint that contains live match data
including individual point scores (15-30-40-Ad), server information,
and point-level statistics.

Endpoint: https://www.flashscore.com/x/feed/d_hh_{match_id}_en_1

This module fetches and parses the feed to extract point-level state.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

FEED_URL = "https://www.flashscore.com/x/feed/d_hh_{match_id}_en_1"

FEED_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.flashscore.com/",
    "x-fsign": "SW9D1eZo",
}

TIMEOUT = 10.0


@dataclass
class PointSnapshot:
    set_number: int | None = None
    game_number: int | None = None
    point_a: int | None = None
    point_b: int | None = None
    point_string: str | None = None
    server_name: str | None = None
    is_break_point: bool = False
    is_set_point: bool = False
    is_match_point: bool = False
    is_tiebreak: bool = False
    match_finished: bool = False
    valid: bool = False

    def content_hash(self) -> str:
        payload = json.dumps(
            {
                "sn": self.set_number,
                "gn": self.game_number,
                "pa": self.point_a,
                "pb": self.point_b,
                "ps": self.point_string,
                "sv": self.server_name,
                "bp": self.is_break_point,
                "sp": self.is_set_point,
                "mp": self.is_match_point,
                "tb": self.is_tiebreak,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


def poll_point_state(
    tracked_match_id: int, flashscore_match_id: str,
) -> PointSnapshot:
    url = FEED_URL.format(match_id=flashscore_match_id)
    try:
        with httpx.Client(
            headers=FEED_HEADERS, timeout=TIMEOUT, follow_redirects=True,
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return _parse_feed(resp.text, tracked_match_id, flashscore_match_id)
    except httpx.HTTPStatusError as e:
        logger.debug("Point feed HTTP error for %s: %d", flashscore_match_id, e.response.status_code)
    except Exception as e:
        logger.debug("Point feed failed for %s: %s", flashscore_match_id, e)
    return PointSnapshot()


def _parse_feed(
    raw: str, tracked_match_id: int, match_id: str,
) -> PointSnapshot:
    if not raw or not raw.strip():
        return PointSnapshot()

    parts = raw.split("¬")
    if len(parts) < 3:
        return PointSnapshot()

    snap = PointSnapshot(valid=True)

    try:
        division = parts[0].split("÷")
        if len(division) >= 4:
            status_code = division[3]
            if status_code in ("100", "110", "120"):
                snap.match_finished = True
    except (IndexError, ValueError):
        pass

    try:
        pieces: dict[str, Any] = {}
        for piece in parts:
            if "÷" in piece:
                div_parts = piece.split("÷")
                key = div_parts[0]
                val = div_parts[-1] if len(div_parts) > 1 else None
                if key not in pieces:
                    pieces[key] = val

        stg_raw = pieces.get("STG", "")
        if isinstance(stg_raw, str) and stg_raw:
            stg_parts = stg_raw.split("|")
            for stg in stg_parts:
                stg_div = stg.split("÷")
                if len(stg_div) >= 5:
                    try:
                        snap.set_number = int(stg_div[0])
                    except (ValueError, IndexError):
                        pass
                    try:
                        snap.game_number = int(stg_div[1])
                    except (ValueError, IndexError):
                        pass
                    try:
                        snap.point_a = int(stg_div[2])
                    except (ValueError, IndexError):
                        pass
                    try:
                        snap.point_b = int(stg_div[3])
                    except (ValueError, IndexError):
                        pass
                    snap.point_string = str(stg_div[4]) if len(stg_div) > 4 else None

        srv_raw = pieces.get("SRV", "")
        if isinstance(srv_raw, str) and srv_raw:
            snap.server_name = srv_raw

        bp_raw = pieces.get("BP", "")
        snap.is_break_point = bp_raw == "1"

        sp_raw = pieces.get("SP", "")
        snap.is_set_point = sp_raw == "1"

        mp_raw = pieces.get("MP", "")
        snap.is_match_point = mp_raw == "1"

        tr_raw = pieces.get("TR", "")
        snap.is_tiebreak = tr_raw == "1"

    except Exception:
        logger.debug("Point feed parse error for %s", match_id, exc_info=True)

    if snap.point_a is None and snap.point_b is None:
        snap.valid = False

    return snap
