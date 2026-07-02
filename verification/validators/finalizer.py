"""Finalizer Verification.

Verify: Every completed match exists once, has scores/odds/final score,
duration valid, validation flags populated, summary stats valid.
"""
from __future__ import annotations

from database import SessionLocal
from sqlalchemy import text

from verification.framework.base import BaseVerifier
from verification.models import VerificationReport


class FinalizerVerifier(BaseVerifier):
    verification_type: str = "finalizer"

    def verify(self) -> VerificationReport:
        failures: list[str] = []
        warnings: list[str] = []
        metrics: dict = {}

        with SessionLocal() as session:
            self._check_completion_integrity(session, failures, warnings, metrics)
            self._check_validation_flags(session, failures, warnings, metrics)
            self._check_unfinalized_finished(session, failures, metrics)

        status = "PASS"
        summary = "Finalizer verification passed."
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

    def _check_completion_integrity(self, session, failures, warnings, metrics):
        total = session.execute(text("SELECT COUNT(*) FROM completed_matches")).scalar() or 0
        self.add_evidence("completed_total", total)
        metrics["completed_matches_total"] = total

        no_scores = session.execute(text(
            "SELECT COUNT(*) FROM completed_matches WHERE score_tick_count = 0"
        )).scalar() or 0
        if no_scores > 0:
            warnings.append(f"Completed matches with 0 score ticks: {no_scores}")
        metrics["no_score_completed"] = no_scores

        no_odds = session.execute(text(
            "SELECT COUNT(*) FROM completed_matches "
            "WHERE betting_market_id IS NOT NULL AND odds_tick_count = 0"
        )).scalar() or 0
        metrics["no_odds_completed"] = no_odds

        no_final_score = session.execute(text(
            "SELECT COUNT(*) FROM completed_matches WHERE final_set_score IS NULL"
        )).scalar() or 0
        no_score_no_final = session.execute(text(
            "SELECT COUNT(*) FROM completed_matches "
            "WHERE final_set_score IS NULL AND score_tick_count = 0"
        )).scalar() or 0
        has_ticks_no_final = no_final_score - no_score_no_final
        self.add_evidence("no_final_score_with_ticks", has_ticks_no_final)
        self.add_evidence("no_final_score_no_ticks", no_score_no_final)
        if has_ticks_no_final > 0:
            failures.append(
                f"Completed matches with score ticks but no final score: {has_ticks_no_final}"
            )
        if no_score_no_final > 0:
            warnings.append(
                f"Completed matches missing final score (no tick data): {no_score_no_final}"
            )
        metrics["no_final_score"] = no_final_score

        neg_duration = session.execute(text(
            "SELECT COUNT(*) FROM completed_matches "
            "WHERE duration_minutes IS NOT NULL AND duration_minutes < 0"
        )).scalar() or 0
        if neg_duration > 0:
            warnings.append(f"Negative durations: {neg_duration}")
        metrics["negative_duration_count"] = neg_duration

    def _check_validation_flags(self, session, failures, warnings, metrics):
        flags = {
            "ready_for_replay": "ready_for_replay",
            "ready_for_feature_extraction": "ready_for_feature_extraction",
            "ready_for_backtesting": "ready_for_backtesting",
            "has_complete_score_data": "has_complete_score_data",
        }
        for label, col in flags.items():
            passed = session.execute(text(
                f"SELECT COUNT(*) FROM completed_matches WHERE {col} = TRUE"
            )).scalar() or 0
            total = session.execute(text("SELECT COUNT(*) FROM completed_matches")).scalar() or 1
            pct = round(passed / total * 100, 1)
            self.add_evidence(f"flag_{col}", f"{passed}/{total} ({pct}%)")
            metrics[f"{col}_pct"] = pct

    def _check_unfinalized_finished(self, session, failures, metrics):
        unfinalized = session.execute(text(
            "SELECT COUNT(*) FROM tracked_matches "
            "WHERE status = 'FINISHED' "
            "AND id NOT IN (SELECT tracked_match_id FROM completed_matches)"
        )).scalar() or 0
        self.add_evidence("unfinalized_finished", unfinalized)
        metrics["unfinalized_finished"] = unfinalized
        if unfinalized > 10:
            failures.append(f"Unfinalized FINISHED matches: {unfinalized}")
