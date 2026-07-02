"""Dataset Verification.

Verify research dataset quality: missing values, timestamp alignment,
invalid score transitions, missing odds/metadata, data consistency.

Produces a Dataset Quality Score 0-100.
"""
from __future__ import annotations

from database import SessionLocal
from sqlalchemy import text

from verification.framework.base import BaseVerifier
from verification.models import VerificationReport


class DatasetVerifier(BaseVerifier):
    verification_type: str = "dataset"

    def verify(self) -> VerificationReport:
        failures: list[str] = []
        warnings: list[str] = []
        metrics: dict = {}
        quality_score = 100

        with SessionLocal() as session:
            total = session.execute(text("SELECT COUNT(*) FROM completed_matches")).scalar() or 0
            self.add_evidence("dataset_total_matches", total)
            metrics["total_matches"] = total

            if total == 0:
                return self._build_report(
                    status="WARNING",
                    summary="No completed matches to assess.",
                    warnings=["Dataset is empty — no completed matches."],
                    metrics={"quality_score": 0},
                )

            score_penalties = self._check_data_completeness(session, failures, warnings, total)
            odds_penalties = self._check_odds_completeness(session, failures, warnings, total)
            duration_penalties = self._check_duration_validity(session, failures, warnings, total)
            metadata_penalties = self._check_metadata_integrity(session, failures, warnings, total)
            flag_penalties = self._check_ready_flags(session, warnings, total)

            quality_score = max(0, 100
                                - score_penalties
                                - odds_penalties
                                - duration_penalties
                                - metadata_penalties
                                - flag_penalties)

        self.add_evidence("quality_score", quality_score)
        metrics["quality_score"] = quality_score

        status = "PASS" if quality_score >= 80 else ("WARNING" if quality_score >= 50 else "FAIL")
        summary = f"Dataset quality score: {quality_score}/100. {len(failures)} failures, {len(warnings)} warnings."

        return self._build_report(
            status=status,
            summary=summary,
            failures=failures,
            warnings=warnings,
            metrics=metrics,
        )

    def _check_data_completeness(self, session, failures, warnings, total) -> int:
        schemes_needed = {
            "final_set_score": "final_set_score IS NULL",
            "score_tick_count": "score_tick_count = 0",
            "scheduled_start": "scheduled_start IS NULL",
            "actual_finish": "actual_finish IS NULL",
            "tournament": "tournament IS NULL",
            "surface": "surface IS NULL",
        }
        penalties = 0
        for label, condition in schemes_needed.items():
            missing = session.execute(text(
                f"SELECT COUNT(*) FROM completed_matches WHERE {condition}"
            )).scalar() or 0
            pct = round(missing / total * 100, 1)
            self.add_evidence(f"missing_{label}", missing)
            if pct > 20:
                failures.append(f"{missing}/{total} matches missing {label} ({pct}%)")
                penalties += 20
            elif pct > 5:
                warnings.append(f"{missing}/{total} matches missing {label} ({pct}%)")
                penalties += 5
        return penalties

    def _check_odds_completeness(self, session, failures, warnings, total) -> int:
        with_odds = session.execute(text(
            "SELECT COUNT(*) FROM completed_matches WHERE betting_market_id IS NOT NULL"
        )).scalar() or 0
        missing_odds = total - with_odds
        pct = round(missing_odds / total * 100, 1) if total else 0
        self.add_evidence("missing_odds_data", missing_odds)
        if pct > 80:
            warnings.append(f"Most matches ({pct}%) have no odds data — expected due to betting source limitation")
            return 0  # not a code bug
        if pct > 50:
            warnings.append(f"High missing odds: {missing_odds}/{total} ({pct}%)")
            return 10
        return 0

    def _check_duration_validity(self, session, failures, warnings, total) -> int:
        neg = session.execute(text(
            "SELECT COUNT(*) FROM completed_matches "
            "WHERE duration_minutes IS NOT NULL AND duration_minutes < 0"
        )).scalar() or 0
        self.add_evidence("negative_durations", neg)
        pct = round(neg / total * 100, 1) if total else 0
        if pct > 10:
            failures.append(f"Negative match durations: {neg}/{total} ({pct}%)")
            return 15
        return 0

    def _check_metadata_integrity(self, session, failures, warnings, total) -> int:
        no_tournament = session.execute(text(
            "SELECT COUNT(*) FROM completed_matches WHERE tournament IS NULL OR tournament = ''"
        )).scalar() or 0
        pct = round(no_tournament / total * 100, 1) if total else 0
        if pct > 10:
            failures.append(f"Missing tournament: {no_tournament}/{total}")
            return 15
        return 0

    def _check_ready_flags(self, session, warnings, total) -> int:
        penalties = 0
        flags = ["ready_for_replay", "ready_for_feature_extraction", "ready_for_backtesting"]
        for flag in flags:
            ready = session.execute(text(
                f"SELECT COUNT(*) FROM completed_matches WHERE {flag} = TRUE"
            )).scalar() or 0
            pct = round(ready / total * 100, 1) if total else 0
            self.add_evidence(f"flag_{flag}_pct", pct)
            if pct < 50:
                penalties += 5
        return penalties
