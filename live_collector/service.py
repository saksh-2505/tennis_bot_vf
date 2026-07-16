"""Live collection background loop.

Runs in a daemon thread spawned by ``run_platform()``.  For every LIVE
match it polls Flashscore scores (every 10 s) and betting odds (every
2 s) independently, writing only when data changes (hash-deduplicated).
"""

import asyncio
import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from config import settings

logger = logging.getLogger(__name__)

# In-memory dedup caches — cleared on restart, DB constraint catches restarts.
_score_hash: dict[int, str] = {}
_odds_hash: dict[int, str] = {}
_point_hash: dict[int, str] = {}
_collection_active: bool = False

# Heartbeat: updated every tick so the incident monitor can detect
# a running-but-silent collector.
_last_tick_ts: float = 0.0

# Lazy betting matching: throttle to once per 60s
_last_betting_match_ts: float = 0.0
_BETTING_MATCH_INTERVAL = 60.0


@dataclass
class MatchState:
    set_score_a: int | None = None
    set_score_b: int | None = None
    game_score_a: int | None = None
    game_score_b: int | None = None
    point_score: str | None = None
    server: str | None = None
    is_tiebreak: bool = False
    match_finished: bool = False

    def state_hash(self) -> str:
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

    def changed_from(self, prev: "MatchState | None") -> dict | None:
        if prev is None:
            return {"type": "initial"}
        changes = {}

        if self.set_score_a != prev.set_score_a or self.set_score_b != prev.set_score_b:
            changes["set_changed"] = {
                "from": f"{prev.set_score_a}-{prev.set_score_b}",
                "to": f"{self.set_score_a}-{self.set_score_b}",
            }
        if self.game_score_a != prev.game_score_a or self.game_score_b != prev.game_score_b:
            changes["game_changed"] = {
                "from": f"{prev.game_score_a}-{prev.game_score_b}",
                "to": f"{self.game_score_a}-{self.game_score_b}",
            }
        if self.point_score != prev.point_score:
            changes["point_changed"] = {
                "from": prev.point_score,
                "to": self.point_score,
            }
        if self.server != prev.server:
            changes["server_changed"] = {
                "from": prev.server,
                "to": self.server,
            }
        if self.is_tiebreak != prev.is_tiebreak:
            changes["tiebreak_changed"] = True
        if self.match_finished and not prev.match_finished:
            changes["match_finished"] = True

        return changes if changes else None

    @classmethod
    def from_snapshot(cls, snap) -> "MatchState":
        return cls(
            set_score_a=snap.set_score_a,
            set_score_b=snap.set_score_b,
            game_score_a=snap.game_score_a,
            game_score_b=snap.game_score_b,
            point_score=snap.point_score,
            server=snap.server,
            is_tiebreak=snap.is_tiebreak,
            match_finished=snap.match_finished,
        )


_score_state: dict[int, MatchState] = {}
_score_game_key: dict[int, str] = {}
_set_hash: dict[tuple[int, int], str] = {}


def get_heartbeat() -> float:
    return _last_tick_ts


def run_live_collection_loop() -> None:
    """Entry point for the background daemon thread."""
    global _collection_active
    if _collection_active:
        return
    _collection_active = True

    logger.info(
        "Live collection loop started "
        "(score_interval=%ds, odds_interval=%ds)",
        settings.LIVE_SCORE_INTERVAL_SECONDS,
        settings.LIVE_ODDS_INTERVAL_SECONDS,
    )

    while True:
        try:
            live = _get_live_matches()
            if not live:
                time.sleep(settings.LIVE_ODDS_INTERVAL_SECONDS)
                continue

            asyncio.run(_collect_tick(live))
        except Exception:
            logger.exception("Live collection tick failed")

        _update_heartbeat()
        time.sleep(settings.LIVE_ODDS_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _get_live_matches() -> list[dict]:
    import database as db
    from models.tracked_match import TrackedMatch

    now = datetime.now(timezone.utc)
    five_min = now + __import__("datetime").timedelta(
        minutes=settings.LIVE_PREFETCH_MINUTES
    )

    with db.SessionLocal() as session:
        walkover_keywords = ["walkover", "w/o", "ret.", "retired", "retirement",
                           "cancelled", "canceled", "postponed", "abandoned"]

        pending = (
            session.query(TrackedMatch)
            .filter(
                TrackedMatch.status.in_(["DISCOVERED", "SCHEDULED"]),
                TrackedMatch.tracking_enabled.is_(True),
            )
            .all()
        )
        for m in pending:
            t = (m.tournament or "").lower()
            if any(kw in t for kw in walkover_keywords):
                m.status = "FINISHED"
                m.actual_finish = now
                logger.info(
                    "Walkover detected: %s vs %s (%s) — marking FINISHED",
                    m.player1_name, m.player2_name, m.tournament,
                )
        if any(m.status == "FINISHED" for m in pending):
            session.commit()

        upcoming = (
            session.query(TrackedMatch)
            .filter(
                TrackedMatch.status.in_(["DISCOVERED", "SCHEDULED"]),
                TrackedMatch.tracking_enabled.is_(True),
                TrackedMatch.scheduled_start.isnot(None),
                TrackedMatch.scheduled_start <= five_min,
                TrackedMatch.live_url.is_(None),
            )
            .all()
        )
        for m in upcoming:
            m.live_url = _flashscore_url(m.flashscore_match_id)
        if upcoming:
            session.commit()

        result = (
            session.query(TrackedMatch)
            .filter(
                TrackedMatch.status == "LIVE",
                TrackedMatch.tracking_enabled.is_(True),
            )
            .all()
        )

        _try_lazy_betting_match(session, result)

        return [
            {
                "id": m.id,
                "flashscore_match_id": m.flashscore_match_id,
                "betting_market_id": m.betting_market_id,
            }
            for m in result
        ]


def _try_lazy_betting_match(session, live_matches: list) -> None:
    """Periodically try to find betting markets for LIVE matches that have none.

    The betting site may add events for matches after the discovery cycle
    (which runs every 12h).  This lazy matcher runs every 60s using the
    confidence-based matcher engine.
    """
    global _last_betting_match_ts

    now = time.monotonic()
    if now - _last_betting_match_ts < _BETTING_MATCH_INTERVAL:
        return
    _last_betting_match_ts = now

    unmatched = [m for m in live_matches if not m.betting_market_id]
    if not unmatched:
        return

    from models.bettingsite import BettingsiteFoundMatch
    from matcher.engine import continuous_retry

    bt_events_raw = session.query(BettingsiteFoundMatch).all()
    if not bt_events_raw:
        return

    bt_events = [
        {
            "name": f"{bt.player_a} v {bt.player_b}",
            "market_id": bt.market_id,
            "runner_a": bt.player_a,
            "runner_b": bt.player_b,
            "date": bt.event_date or "",
            "comp_name": bt.comp_name or "",
        }
        for bt in bt_events_raw
    ]

    assigned = continuous_retry(session, unmatched, bt_events)
    if assigned:
        logger.info(
            "Continuous retry: assigned %d markets to previously unmatched LIVE matches",
            assigned,
        )


async def _collect_tick(matches: list[dict]) -> None:
    """Poll all live matches concurrently, batch-insert new ticks.

    Scores are polled every 5 s (throttled per match).  Odds are polled
    every 3 s.  Both are hash-deduplicated — only changed data is
    inserted.  Gap detection interpolates missed game states.
    """
    score_batch: list[dict] = []
    odds_batch: list[dict] = []

    async def _handle_one(m: dict) -> None:
        mid = m["id"]

        # -- scores (every 5 s) ------------------------------------------
        if _score_due(mid):
            from live_collector.flashscore_live import (
                ScoreSnapshot,
                mark_match_finished,
                poll_flashscore_score,
                _detect_gaps,
            )

            snap: ScoreSnapshot = await asyncio.to_thread(
                poll_flashscore_score, mid, m["flashscore_match_id"]
            )

            new_state = MatchState.from_snapshot(snap)
            prev_state = _score_state.get(mid)
            changes = new_state.changed_from(prev_state)
            h = new_state.state_hash()

            if h != _score_hash.get(mid):
                _score_hash[mid] = h
                _score_state[mid] = new_state
                now_ts = datetime.now(timezone.utc)

                # Primary tick: actual polled state
                score_batch.append({
                    "tracked_match_id": mid,
                    "flashscore_match_id": m["flashscore_match_id"],
                    "timestamp": now_ts,
                    "set_score_a": snap.set_score_a,
                    "set_score_b": snap.set_score_b,
                    "game_score_a": snap.game_score_a,
                    "game_score_b": snap.game_score_b,
                    "point_score": snap.point_score,
                    "server": snap.server,
                    "is_tiebreak": snap.is_tiebreak,
                    "match_finished": snap.match_finished,
                    "source": "polled",
                    "content_hash": h,
                })

                # Gap detection: interpolate missed game states
                _prev_game_key = _score_game_key.get(mid)
                if snap.game_score_a is not None and snap.game_score_b is not None:
                    current_key = "{}-{}".format(snap.game_score_a, snap.game_score_b)
                    gaps = _detect_gaps(
                        _prev_game_key,
                        snap.game_score_a,
                        snap.game_score_b,
                    )
                    for ga, gb in gaps:
                        gap_hash = hashlib.sha256(
                            json.dumps({
                                "sa": snap.set_score_a,
                                "sb": snap.set_score_b,
                                "ga": ga, "gb": gb,
                            }, sort_keys=True).encode()
                        ).hexdigest()
                        score_batch.append({
                            "tracked_match_id": mid,
                            "flashscore_match_id": m["flashscore_match_id"],
                            "timestamp": now_ts,
                            "set_score_a": snap.set_score_a,
                            "set_score_b": snap.set_score_b,
                            "game_score_a": ga,
                            "game_score_b": gb,
                            "point_score": None,
                            "server": None,
                            "is_tiebreak": snap.is_tiebreak,
                            "match_finished": False,
                            "source": "interpolated",
                            "content_hash": gap_hash,
                        })
                    _score_game_key[mid] = current_key

                # Per-set game history: store completed set scores
                for gs in snap.per_set_games:
                    if gs.set_number > 0 and (
                        snap.set_score_a is not None
                        and snap.set_score_b is not None
                    ):
                        set_hash = hashlib.sha256(
                            json.dumps({
                                "set": gs.set_number,
                                "ga": gs.game_a,
                                "gb": gs.game_b,
                            }, sort_keys=True).encode()
                        ).hexdigest()
                        if set_hash != _set_hash.get((mid, gs.set_number)):
                            _set_hash[(mid, gs.set_number)] = set_hash
                            score_batch.append({
                                "tracked_match_id": mid,
                                "flashscore_match_id": m["flashscore_match_id"],
                                "timestamp": now_ts,
                                "set_score_a": gs.set_number,
                                "set_score_b": None,
                                "game_score_a": gs.game_a,
                                "game_score_b": gs.game_b,
                                "point_score": None,
                                "server": None,
                                "is_tiebreak": False,
                                "match_finished": False,
                                "source": "set_history",
                                "content_hash": set_hash,
                            })

                if changes:
                    logger.debug(
                        "Match %d state change: %s",
                        mid,
                        " | ".join(changes.keys()),
                    )

                # Event-synchronized odds: capture odds NOW on state change
                bmid = m.get("betting_market_id")
                if changes and bmid:
                    from live_collector.betting_live import OddsSnapshot, poll_betting_odds

                    odds_snap: OddsSnapshot = await asyncio.to_thread(
                        poll_betting_odds, bmid,
                    )
                    if odds_snap.any_valid():
                        oh = odds_snap.content_hash()
                        if oh != _odds_hash.get(mid):
                            _odds_hash[mid] = oh
                            odds_batch.append({
                                "tracked_match_id": mid,
                                "betting_market_id": bmid,
                                "timestamp": now_ts,
                                "back_odds_a": odds_snap.back_odds_a,
                                "back_odds_b": odds_snap.back_odds_b,
                                "lay_odds_a": odds_snap.lay_odds_a,
                                "lay_odds_b": odds_snap.lay_odds_b,
                                "volume_a": odds_snap.volume_a,
                                "volume_b": odds_snap.volume_b,
                                "content_hash": oh,
                            })

            if snap.match_finished:
                mark_match_finished(mid)
                _cleanup_match(mid)

        # -- odds (every 2 s, only if no score-driven capture happened) ---
        bmid = m.get("betting_market_id")
        if bmid and mid not in {r["tracked_match_id"] for r in odds_batch}:
            from live_collector.betting_live import OddsSnapshot, poll_betting_odds

            odds_snap: OddsSnapshot = await asyncio.to_thread(
                poll_betting_odds, bmid
            )

            if odds_snap.any_valid():
                h = odds_snap.content_hash()
                if h != _odds_hash.get(mid):
                    _odds_hash[mid] = h
                    odds_batch.append({
                        "tracked_match_id": mid,
                        "betting_market_id": bmid,
                        "timestamp": datetime.now(timezone.utc),
                        "back_odds_a": odds_snap.back_odds_a,
                        "back_odds_b": odds_snap.back_odds_b,
                        "lay_odds_a": odds_snap.lay_odds_a,
                        "lay_odds_b": odds_snap.lay_odds_b,
                        "volume_a": odds_snap.volume_a,
                        "volume_b": odds_snap.volume_b,
                        "content_hash": h,
                    })

        # -- points (every 3 s, only for matched markets) -----------------
        bmid = m.get("betting_market_id")
        if bmid and _point_due(mid):
            from live_collector.points_live import PointSnapshot, poll_point_state

            pt_snap: PointSnapshot = await asyncio.to_thread(
                poll_point_state, mid, m["flashscore_match_id"],
            )
            if pt_snap.valid:
                ph = pt_snap.content_hash()
                if ph != _point_hash.get(mid):
                    _point_hash[mid] = ph
                    point_batch.append({
                        "tracked_match_id": mid,
                        "flashscore_match_id": m["flashscore_match_id"],
                        "timestamp": datetime.now(timezone.utc),
                        "set_number": pt_snap.set_number,
                        "game_number": pt_snap.game_number,
                        "point_a": pt_snap.point_a,
                        "point_b": pt_snap.point_b,
                        "point_string": pt_snap.point_string,
                        "server_name": pt_snap.server_name,
                        "is_break_point": pt_snap.is_break_point,
                        "is_set_point": pt_snap.is_set_point,
                        "is_match_point": pt_snap.is_match_point,
                        "is_tiebreak": pt_snap.is_tiebreak,
                        "content_hash": ph,
                    })

    point_batch: list[dict] = []

    await asyncio.gather(*(_handle_one(m) for m in matches))

    if score_batch:
        _bulk_insert("live_scores", score_batch)
        logger.info("Inserted %d score ticks for %d matches",
                     len(score_batch), len({r["tracked_match_id"] for r in score_batch}))
    if odds_batch:
        _bulk_insert("live_odds", odds_batch)
        logger.info("Inserted %d odds ticks for %d matches",
                     len(odds_batch), len({r["tracked_match_id"] for r in odds_batch}))
    if point_batch:
        _bulk_insert("live_points", point_batch)
        logger.info("Inserted %d point ticks for %d matches",
                     len(point_batch), len({r["tracked_match_id"] for r in point_batch}))


# ---- score throttling ---------------------------------------------------


_score_last_poll: dict[int, float] = {}


def _score_due(match_id: int) -> bool:
    now = time.monotonic()
    last = _score_last_poll.get(match_id, 0)
    if now - last >= settings.LIVE_SCORE_INTERVAL_SECONDS:
        _score_last_poll[match_id] = now
        return True
    return False


# ---- point throttling ----------------------------------------------------

_point_last_poll: dict[int, float] = {}
_POINT_INTERVAL = 3.0


def _point_due(match_id: int) -> bool:
    now = time.monotonic()
    last = _point_last_poll.get(match_id, 0)
    if now - last >= _POINT_INTERVAL:
        _point_last_poll[match_id] = now
        return True
    return False


def _cleanup_match(match_id: int) -> None:
    """Remove in-memory dedup/state entries for a finished match."""
    _score_hash.pop(match_id, None)
    _odds_hash.pop(match_id, None)
    _point_hash.pop(match_id, None)
    _score_last_poll.pop(match_id, None)
    _point_last_poll.pop(match_id, None)
    _score_state.pop(match_id, None)
    _score_game_key.pop(match_id, None)
    for k in list(_set_hash.keys()):
        if k[0] == match_id:
            _set_hash.pop(k, None)


# ---- heartbeat -----------------------------------------------------------


def _update_heartbeat() -> None:
    global _last_tick_ts
    _last_tick_ts = time.monotonic()


# ---- bulk insert --------------------------------------------------------


def _bulk_insert(table_name: str, rows: list[dict]) -> None:
    import database as db
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy import table, column

    # Build a lightweight INSERT … ON CONFLICT DO NOTHING
    cols = list(rows[0].keys())
    t = table(
        table_name,
        *[column(c) for c in cols],
    )
    stmt = pg_insert(t).values(rows).on_conflict_do_nothing()

    with db.SessionLocal() as session:
        session.execute(stmt)
        session.commit()


def _flashscore_url(match_id: str) -> str:
    return f"https://www.flashscore.mobi/match/{match_id}/"
