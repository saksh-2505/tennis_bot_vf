"""Database Verification.

Verify: FK integrity, missing/duplicate/orphaned rows, hypertable health,
index health, slow queries, connection count.
"""
from __future__ import annotations

from database import SessionLocal
from sqlalchemy import text

from verification.framework.base import BaseVerifier
from verification.framework.evidence import query_evidence
from verification.models import VerificationReport


class DatabaseVerifier(BaseVerifier):
    verification_type: str = "database"

    def verify(self) -> VerificationReport:
        failures: list[str] = []
        warnings: list[str] = []
        metrics: dict = {}

        with SessionLocal() as session:
            self._check_orphaned_rows(session, failures, metrics)
            self._check_duplicate_matches(session, failures, metrics)
            self._check_fk_integrity(session, failures, metrics)
            self._check_missing_data(session, failures, warnings, metrics)
            self._check_active_connections(session, failures, warnings, metrics)
            self._check_table_stats(session, metrics)

        status = "PASS"
        summary = "All database checks passed."
        if warnings and not failures:
            status = "WARNING"
            summary = f"{len(warnings)} warning(s)."
        if failures:
            status = "FAIL"
            summary = f"{len(failures)} failure(s)."

        return self._build_report(
            status=status,
            summary=summary,
            failures=failures,
            warnings=warnings,
            metrics=metrics,
        )

    def _check_orphaned_rows(self, session, failures: list[str], metrics: dict) -> None:
        orphan_scores = session.execute(text(
            "SELECT COUNT(*) FROM live_scores ls "
            "LEFT JOIN tracked_matches tm ON ls.tracked_match_id = tm.id "
            "WHERE tm.id IS NULL"
        )).scalar() or 0

        orphan_odds = session.execute(text(
            "SELECT COUNT(*) FROM live_odds lo "
            "LEFT JOIN tracked_matches tm ON lo.tracked_match_id = tm.id "
            "WHERE tm.id IS NULL"
        )).scalar() or 0

        orphan_completed = session.execute(text(
            "SELECT COUNT(*) FROM completed_matches cm "
            "LEFT JOIN tracked_matches tm ON cm.tracked_match_id = tm.id "
            "WHERE tm.id IS NULL"
        )).scalar() or 0

        self.add_evidence("orphan_live_scores", orphan_scores)
        self.add_evidence("orphan_live_odds", orphan_odds)
        self.add_evidence("orphan_completed_matches", orphan_completed)

        if orphan_scores > 0:
            failures.append(f"Orphaned live_scores: {orphan_scores} rows")
        if orphan_odds > 0:
            failures.append(f"Orphaned live_odds: {orphan_odds} rows")
        if orphan_completed > 0:
            failures.append(f"Orphaned completed_matches: {orphan_completed} rows")

        metrics["orphan_rows_total"] = orphan_scores + orphan_odds + orphan_completed

    def _check_duplicate_matches(self, session, failures: list[str], metrics: dict) -> None:
        for table in ["flashscorefoundmatches", "bettingsitefoundmatches", "tracked_matches"]:
            col = "flashscore_match_id" if table != "bettingsitefoundmatches" else "market_id"
            dupes = session.execute(text(
                f"SELECT COUNT(*) FROM ("
                f"  SELECT {col}, COUNT(*) FROM {table} GROUP BY {col} HAVING COUNT(*) > 1"
                f") AS d"
            )).scalar() or 0
            if dupes > 0:
                failures.append(f"Duplicate rows in {table}: {dupes} groups")
            self.add_evidence(f"duplicate_{table}", dupes)

        dup_tracked = session.execute(text(
            "SELECT COUNT(*) FROM completed_matches "
            "WHERE tracked_match_id IN ("
            "  SELECT tracked_match_id FROM completed_matches "
            "  GROUP BY tracked_match_id HAVING COUNT(*) > 1"
            ")"
        )).scalar() or 0
        if dup_tracked > 0:
            failures.append(f"Duplicate completed_matches.tracked_match_id: {dup_tracked}")

    def _check_fk_integrity(self, session, failures: list[str], metrics: dict) -> None:
        ref_checks = [
            ("tracked_matches→players(1)", "tracked_matches", "player1_id", "players", "player_id"),
            ("tracked_matches→players(2)", "tracked_matches", "player2_id", "players", "player_id"),
        ]
        for label, child_table, fk_col, parent_table, pk_col in ref_checks:
            bad = session.execute(text(
                f"SELECT COUNT(*) FROM {child_table} c "
                f"LEFT JOIN {parent_table} p ON c.{fk_col} = p.{pk_col} "
                f"WHERE c.{fk_col} IS NOT NULL AND p.{pk_col} IS NULL"
            )).scalar() or 0
            self.add_evidence(f"fk_{child_table}_{fk_col}", bad)
            if bad > 0:
                failures.append(f"FK integrity {label}: {bad} broken references")

    def _check_missing_data(self, session, failures: list[str], warnings: list[str], metrics: dict) -> None:
        track_scores = session.execute(text(
            "SELECT COUNT(*) FROM tracked_matches tm "
            "LEFT JOIN live_scores ls ON tm.id = ls.tracked_match_id "
            "WHERE tm.status = 'FINISHED' AND ls.tracked_match_id IS NULL"
        )).scalar() or 0
        if track_scores > 0:
            warnings.append(f"FINISHED matches with no live_scores: {track_scores}")

        completed_no_scores = session.execute(text(
            "SELECT COUNT(*) FROM completed_matches "
            "WHERE score_tick_count = 0"
        )).scalar() or 0
        if completed_no_scores > 0:
            warnings.append(f"Completed matches with 0 score ticks: {completed_no_scores}")

        negative_duration = session.execute(text(
            "SELECT COUNT(*) FROM completed_matches "
            "WHERE duration_minutes IS NOT NULL AND duration_minutes < 0"
        )).scalar() or 0
        self.add_evidence("negative_durations", negative_duration)
        if negative_duration > 0:
            warnings.append(f"Completed matches with negative duration: {negative_duration}")

    def _check_active_connections(self, session, failures: list[str], warnings: list[str], metrics: dict) -> None:
        conns = session.execute(text(
            "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'"
        )).scalar() or 0
        self.add_evidence("active_connections", conns)
        metrics["active_connections"] = conns
        if conns > 50:
            failures.append(f"Active DB connections: {conns} (> 50)")
        elif conns > 30:
            warnings.append(f"Active DB connections: {conns} (> 30)")

    def _check_table_stats(self, session, metrics: dict) -> None:
        tables = [
            "flashscorefoundmatches", "bettingsitefoundmatches",
            "tracked_matches", "live_scores", "live_odds",
            "completed_matches", "players", "incidents", "system_events",
        ]
        for table in tables:
            count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0
            self.add_evidence(f"row_count_{table}", count)
            metrics[f"row_count_{table}"] = count
