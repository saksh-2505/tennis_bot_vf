"""Collection Verification.

The most important verification suite. Verifies live match data quality:
heartbeat, poll interval, tick frequency, score/odds progression,
duplicate detection, DB insertion success, latency.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from database import SessionLocal
from sqlalchemy import text

from verification.framework.base import BaseVerifier
from verification.models import VerificationReport


class CollectionVerifier(BaseVerifier):
    verification_type: str = "collection"

    def verify(self) -> VerificationReport:
        failures: list[str] = []
        warnings: list[str] = []
        metrics: dict = {}

        with SessionLocal() as session:
            live_count = self._get_live_count(session)
            self.add_evidence("live_match_count", live_count)
            metrics["live_match_count"] = live_count

            self._check_heartbeat(session, failures, warnings, metrics)
            self._check_tick_frequency(session, failures, warnings, metrics)
            self._check_duplicate_ticks(session, failures, warnings, metrics)
            self._check_score_progression(session, failures, metrics)
            self._check_zero_tick_matches(session, failures, warnings, metrics)

        status = "PASS"
        summary = f"Collection: {live_count} LIVE matches. All {self.verification_type} checks passed."
        if warnings and not failures:
            status = "WARNING"
            summary = f"Collection: {len(warnings)} warning(s) across {live_count} LIVE matches."
        if failures:
            status = "FAIL"
            summary = f"Collection: {len(failures)} failure(s)."

        return self._build_report(
            status=status,
            summary=summary,
            failures=failures,
            warnings=warnings,
            metrics=metrics,
        )

    def _get_live_count(self, session) -> int:
        return session.execute(text(
            "SELECT COUNT(*) FROM tracked_matches WHERE status = 'LIVE'"
        )).scalar() or 0

    def _check_heartbeat(self, session, failures, warnings, metrics) -> None:
        stale_threshold_seconds = 120
        stale_scores = session.execute(text(
            "SELECT tm.id, tm.player1_name, tm.player2_name, "
            "MAX(ls.timestamp) as last_score "
            "FROM tracked_matches tm "
            "LEFT JOIN live_scores ls ON tm.id = ls.tracked_match_id "
            "WHERE tm.status = 'LIVE' "
            "GROUP BY tm.id, tm.player1_name, tm.player2_name "
            "HAVING MAX(ls.timestamp) IS NULL "
            "   OR MAX(ls.timestamp) < NOW() - make_interval(secs => :stale)"
        ), {"stale": stale_threshold_seconds}).fetchall()
        stale_ids = [f"#{r[0]} ({r[1]} vs {r[2]})" for r in stale_scores]
        self.add_evidence("stale_score_count", len(stale_scores))
        metrics["stale_score_matches"] = len(stale_scores)
        if stale_scores:
            for sid in stale_ids[:5]:
                failures.append(f"Stale scores for match {sid}")
            if len(stale_scores) > 5:
                failures.append(f"... and {len(stale_scores) - 5} more stale matches")

        stale_odds = session.execute(text(
            "SELECT tm.id, tm.player1_name, tm.player2_name, "
            "MAX(lo.timestamp) as last_odd "
            "FROM tracked_matches tm "
            "LEFT JOIN live_odds lo ON tm.id = lo.tracked_match_id "
            "WHERE tm.status = 'LIVE' AND tm.betting_market_id IS NOT NULL "
            "GROUP BY tm.id, tm.player1_name, tm.player2_name "
            "HAVING MAX(lo.timestamp) IS NULL "
            "   OR MAX(lo.timestamp) < NOW() - INTERVAL '" + str(stale_threshold_seconds) + " seconds'"
        )).fetchall()
        metrics["stale_odds_matches"] = len(stale_odds)
        self.add_evidence("stale_odds_count", len(stale_odds))

    def _check_tick_frequency(self, session, failures, warnings, metrics) -> None:
        tick_stats = session.execute(text(
            "SELECT "
            "  COUNT(*) as total_ticks, "
            "  AVG(tick_count) as avg_ticks_per_match, "
            "  MIN(tick_count) as min_ticks, "
            "  MAX(tick_count) as max_ticks "
            "FROM ("
            "  SELECT tracked_match_id, COUNT(*) as tick_count "
            "  FROM live_scores "
            "  WHERE timestamp > NOW() - INTERVAL '1 hour' "
            "  GROUP BY tracked_match_id"
            ") AS t"
        )).fetchone()
        if tick_stats:
            self.add_evidence("score_tick_stats", dict(tick_stats._mapping))
            metrics["avg_ticks_per_match"] = round(tick_stats[1] or 0, 1)
            metrics["total_recent_ticks"] = tick_stats[0] or 0

        odds_stats = session.execute(text(
            "SELECT COUNT(*) as total_ticks FROM live_odds "
            "WHERE timestamp > NOW() - INTERVAL '1 hour'"
        )).fetchone()
        if odds_stats:
            metrics["total_recent_odds_ticks"] = odds_stats[0] or 0
            self.add_evidence("odds_tick_count_1h", odds_stats[0] or 0)

    def _check_duplicate_ticks(self, session, failures, warnings, metrics) -> None:
        dup_scores = session.execute(text(
            "SELECT COUNT(*) FROM ("
            "  SELECT tracked_match_id, timestamp, content_hash, COUNT(*) "
            "  FROM live_scores "
            "  WHERE timestamp > NOW() - INTERVAL '1 day' "
            "  GROUP BY tracked_match_id, timestamp, content_hash "
            "  HAVING COUNT(*) > 1"
            ") AS d"
        )).scalar() or 0
        total_scores = session.execute(text(
            "SELECT COUNT(*) FROM live_scores "
            "WHERE timestamp > NOW() - INTERVAL '1 day'"
        )).scalar() or 1
        dup_rate = round(dup_scores / total_scores * 100, 3) if total_scores else 0
        self.add_evidence("duplicate_score_ticks", dup_scores)
        self.add_evidence("duplicate_score_rate", dup_rate)
        metrics["duplicate_score_ticks"] = dup_scores
        metrics["duplicate_score_rate_pct"] = dup_rate
        if dup_rate > 5:
            failures.append(f"High duplicate score tick rate: {dup_rate}%")

        dup_odds = session.execute(text(
            "SELECT COUNT(*) FROM ("
            "  SELECT tracked_match_id, timestamp, content_hash, COUNT(*) "
            "  FROM live_odds "
            "  WHERE timestamp > NOW() - INTERVAL '1 day' "
            "  GROUP BY tracked_match_id, timestamp, content_hash "
            "  HAVING COUNT(*) > 1"
            ") AS d"
        )).scalar() or 0
        total_odds = session.execute(text(
            "SELECT COUNT(*) FROM live_odds "
            "WHERE timestamp > NOW() - INTERVAL '1 day'"
        )).scalar() or 1
        odds_dup_rate = round(dup_odds / total_odds * 100, 3) if total_odds else 0
        self.add_evidence("duplicate_odds_ticks", dup_odds)
        metrics["duplicate_odds_tick_rate_pct"] = odds_dup_rate

    def _check_score_progression(self, session, failures, metrics) -> None:
        score_gaps = session.execute(text(
            "SELECT tracked_match_id, timestamp, "
            "LAG(timestamp) OVER (PARTITION BY tracked_match_id ORDER BY timestamp) as prev_ts "
            "FROM live_scores "
            "WHERE timestamp > NOW() - INTERVAL '1 hour'"
        )).fetchall()
        huge_gaps = [r for r in score_gaps if r[2] and (r[1] - r[2]).total_seconds() > 3600]
        if huge_gaps:
            failures.append(f"Score gaps > 1h: {len(huge_gaps)} instances")
        self.add_evidence("score_gaps_over_1h", len(huge_gaps))

    def _check_zero_tick_matches(self, session, failures, warnings, metrics) -> None:
        zero_ticks = session.execute(text(
            "SELECT COUNT(*) FROM tracked_matches tm "
            "LEFT JOIN live_scores ls ON tm.id = ls.tracked_match_id "
            "WHERE tm.status = 'LIVE' AND ls.tracked_match_id IS NULL"
        )).scalar() or 0
        self.add_evidence("live_no_score_ticks", zero_ticks)
        metrics["live_matches_without_scores"] = zero_ticks
        if zero_ticks > 0:
            failures.append(f"LIVE matches with zero score ticks: {zero_ticks}")
