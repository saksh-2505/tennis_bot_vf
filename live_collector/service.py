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
        # Pre-fetch URLs for matches about to start
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

        # Fetch all LIVE matches
        result = (
            session.query(TrackedMatch)
            .filter(
                TrackedMatch.status == "LIVE",
                TrackedMatch.tracking_enabled.is_(True),
            )
            .all()
        )

        # Lazy betting market matching for matches without odds
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

    Scores are polled every 10 s (throttled per match).  Odds are polled
    every 2 s.  Both are hash-deduplicated — only changed data is
    inserted.
    """
    score_batch: list[dict] = []
    odds_batch: list[dict] = []

    async def _handle_one(m: dict) -> None:
        mid = m["id"]

        # -- scores (every 10 s) ------------------------------------------
        if _score_due(mid):
            from live_collector.flashscore_live import (
                ScoreSnapshot,
                mark_match_finished,
                poll_flashscore_score,
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

                score_batch.append({
                    "tracked_match_id": mid,
                    "flashscore_match_id": m["flashscore_match_id"],
                    "timestamp": datetime.now(timezone.utc),
                    "set_score_a": snap.set_score_a,
                    "set_score_b": snap.set_score_b,
                    "game_score_a": snap.game_score_a,
                    "game_score_b": snap.game_score_b,
                    "point_score": snap.point_score,
                    "server": snap.server,
                    "is_tiebreak": snap.is_tiebreak,
                    "match_finished": snap.match_finished,
                    "content_hash": h,
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
                                "timestamp": datetime.now(timezone.utc),
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

    await asyncio.gather(*(_handle_one(m) for m in matches))

    if score_batch:
        _bulk_insert("live_scores", score_batch)
        logger.info("Inserted %d score ticks for %d matches",
                     len(score_batch), len({r["tracked_match_id"] for r in score_batch}))
    if odds_batch:
        _bulk_insert("live_odds", odds_batch)
        logger.info("Inserted %d odds ticks for %d matches",
                     len(odds_batch), len({r["tracked_match_id"] for r in odds_batch}))


# ---- score throttling ---------------------------------------------------


_score_last_poll: dict[int, float] = {}


def _score_due(match_id: int) -> bool:
    now = time.monotonic()
    last = _score_last_poll.get(match_id, 0)
    if now - last >= settings.LIVE_SCORE_INTERVAL_SECONDS:
        _score_last_poll[match_id] = now
        return True
    return False


def _cleanup_match(match_id: int) -> None:
    """Remove in-memory dedup/state entries for a finished match."""
    _score_hash.pop(match_id, None)
    _odds_hash.pop(match_id, None)
    _score_last_poll.pop(match_id, None)
    _score_state.pop(match_id, None)


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
