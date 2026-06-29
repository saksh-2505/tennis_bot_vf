from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from observability import config as obs_config
from observability.models import MatchHealth, PipelineStageStatus


class MatchMonitor:
    def __init__(self) -> None:
        self._match_health: dict[int, MatchHealth] = {}

    def get_match_health(self, tracked_match_id: int) -> MatchHealth | None:
        return self._match_health.get(tracked_match_id)

    def get_all_match_health(self) -> dict[int, MatchHealth]:
        return dict(self._match_health)

    def refresh(self) -> None:
        try:
            from database import SessionLocal
            from sqlalchemy import text
            session = SessionLocal()
            try:
                live_matches = session.execute(text(
                    "SELECT id, status, flashscore_match_id, betting_market_id, "
                    "EXTRACT(EPOCH FROM (NOW() - scheduled_start)) AS duration_seconds "
                    "FROM tracked_matches WHERE status = 'LIVE'"
                )).fetchall()

                for row in live_matches:
                    mid = row[0]
                    mh = self._match_health.get(mid) or MatchHealth(tracked_match_id=mid, status=row[1])
                    mh.match_duration_seconds = float(row[3] or 0)

                    score_row = session.execute(text(
                        "SELECT MAX(timestamp), COUNT(*) FROM live_scores "
                        "WHERE tracked_match_id = :mid AND timestamp > NOW() - INTERVAL '5 minutes'",
                        {"mid": mid},
                    )).fetchone()
                    mh.last_score_timestamp = score_row[0]
                    if score_row[1] and score_row[0]:
                        mh.score_tick_rate = float(score_row[1]) / 300.0

                    odds_row = session.execute(text(
                        "SELECT MAX(timestamp), COUNT(*) FROM live_odds "
                        "WHERE tracked_match_id = :mid AND timestamp > NOW() - INTERVAL '5 minutes'",
                        {"mid": mid},
                    )).fetchone()
                    mh.last_odds_timestamp = odds_row[0]
                    if odds_row[1] and odds_row[0]:
                        mh.odds_tick_rate = float(odds_row[1]) / 300.0

                    score_stale = obs_config.OBSERVABILITY_MATCH_SCORE_STALE_SECONDS
                    odds_stale = obs_config.OBSERVABILITY_MATCH_ODDS_STALE_SECONDS
                    now = datetime.now(timezone.utc)
                    diags = []
                    if mh.last_score_timestamp:
                        score_age = (now - mh.last_score_timestamp).total_seconds()
                        if score_age > score_stale:
                            diags.append(f"score updates stopped ({score_age:.0f}s ago)")
                    if mh.last_odds_timestamp:
                        odds_age = (now - mh.last_odds_timestamp).total_seconds()
                        if odds_age > odds_stale:
                            diags.append(f"odds updates stopped ({odds_age:.0f}s ago)")
                    mh.diagnostics = diags or None
                    self._match_health[mid] = mh

                finished = session.execute(text(
                    "SELECT tm.id FROM tracked_matches tm LEFT JOIN completed_matches cm "
                    "ON tm.id = cm.tracked_match_id WHERE tm.status = 'FINISHED' "
                    "AND cm.id IS NULL AND tm.updated_at < NOW() - INTERVAL '30 minutes'"
                )).fetchall()
                for row in finished:
                    mid = row[0]
                    if mid in self._match_health:
                        mh = self._match_health[mid]
                        if mh.diagnostics is None:
                            mh.diagnostics = []
                        mh.diagnostics.append("finalizer never executed")
            finally:
                session.close()
        except Exception:
            pass

    def validate_match_pipeline(self, tracked_match_id: int) -> dict[str, Any]:
        result: dict[str, Any] = {
            "tracked_match_id": tracked_match_id,
            "stages": [],
            "first_failure": None,
        }
        try:
            from database import SessionLocal
            from sqlalchemy import text
            session = SessionLocal()
            try:
                stages = [
                    ("Discovery", "flashscorefoundmatches",
                     "SELECT COUNT(*) FROM flashscorefoundmatches f "
                     "JOIN tracked_matches t ON f.flashscore_match_id = t.flashscore_match_id "
                     "WHERE t.id = :mid"),
                    ("Registry", "tracked_matches",
                     "SELECT status FROM tracked_matches WHERE id = :mid"),
                    ("Live Collection", "live_scores",
                     "SELECT MAX(timestamp) FROM live_scores WHERE tracked_match_id = :mid"),
                    ("Database Insert", "live_odds",
                     "SELECT MAX(timestamp) FROM live_odds WHERE tracked_match_id = :mid"),
                    ("Finalizer", "completed_matches",
                     "SELECT finalized_at FROM completed_matches WHERE tracked_match_id = :mid"),
                ]

                for stage_name, _table, query in stages:
                    r = session.execute(text(query), {"mid": tracked_match_id}).fetchone()
                    if r is None or r[0] is None:
                        result["stages"].append({"stage": stage_name, "status": "fail", "error": "no data"})
                        if result["first_failure"] is None:
                            result["first_failure"] = stage_name
                    else:
                        result["stages"].append({"stage": stage_name, "status": "pass", "detail": str(r[0])})
            finally:
                session.close()
        except Exception as e:
            result["error"] = str(e)
        return result


_match_monitor_instance: MatchMonitor | None = None


def get_match_monitor() -> MatchMonitor:
    global _match_monitor_instance
    if _match_monitor_instance is None:
        _match_monitor_instance = MatchMonitor()
    return _match_monitor_instance
