"""Pipeline Verification.

End-to-end verification: Flashscore → Parser → Registry → Collector →
Database → Finalizer → Completed Match → Incident → Telegram.

Every stage produces PASS/FAIL with duration. Identifies first failing stage.
"""
from __future__ import annotations

import time

from database import SessionLocal
from sqlalchemy import text

from verification.framework.base import BaseVerifier
from verification.models import VerificationReport


class PipelineVerifier(BaseVerifier):
    verification_type: str = "pipeline"

    def verify(self) -> VerificationReport:
        failures: list[str] = []
        warnings: list[str] = []
        metrics: dict = {}
        stages: list[dict] = []

        with SessionLocal() as session:
            t0 = time.time()
            fs_count = session.execute(text("SELECT COUNT(*) FROM flashscorefoundmatches")).scalar() or 0
            stage1 = self._record_stage("Flashscore Discovery", fs_count > 0, time.time() - t0)
            stages.append(stage1)
            if not stage1["passed"]:
                failures.append("Flashscore: no discovered matches")

            t0 = time.time()
            bt_count = session.execute(text("SELECT COUNT(*) FROM bettingsitefoundmatches")).scalar() or 0
            stage2 = self._record_stage("Betting Discovery", bt_count > 0, time.time() - t0)
            stages.append(stage2)
            if not stage2["passed"]:
                warnings.append("Betting Discovery: no markets discovered")

            t0 = time.time()
            tracked = session.execute(text("SELECT COUNT(*) FROM tracked_matches")).scalar() or 0
            stage3 = self._record_stage("Match Registry", tracked > 0, time.time() - t0)
            stages.append(stage3)
            if not stage3["passed"]:
                failures.append("Registry: no tracked matches")

            t0 = time.time()
            live_count = session.execute(text(
                "SELECT COUNT(*) FROM tracked_matches WHERE status = 'LIVE'"
            )).scalar() or 0
            score_ticks = session.execute(text(
                "SELECT COUNT(*) FROM live_scores WHERE timestamp > NOW() - INTERVAL '1 hour'"
            )).scalar() or 0
            collector_ok = live_count == 0 or score_ticks > 0
            stage4 = self._record_stage("Live Collector", collector_ok, time.time() - t0)
            stages.append(stage4)
            if not stage4["passed"] and live_count > 0:
                failures.append("Live Collector: LIVE matches but no recent score ticks")

            t0 = time.time()
            completed = session.execute(text("SELECT COUNT(*) FROM completed_matches")).scalar() or 0
            finished_unfinalized = session.execute(text(
                "SELECT COUNT(*) FROM tracked_matches "
                "WHERE status = 'FINISHED' "
                "AND id NOT IN (SELECT tracked_match_id FROM completed_matches)"
            )).scalar() or 0
            finalizer_ok = completed > 0 or (live_count > 0 and finished_unfinalized == 0)
            stage5 = self._record_stage("Match Finalizer", finalizer_ok, time.time() - t0)
            stages.append(stage5)
            if finished_unfinalized > 3:
                failures.append(f"Finalizer: {finished_unfinalized} finished matches not finalized")

            t0 = time.time()
            incident_count = session.execute(text("SELECT COUNT(*) FROM incidents")).scalar() or 0
            open_count = session.execute(text(
                "SELECT COUNT(*) FROM incidents WHERE status IN ('OPEN', 'ACKNOWLEDGED')"
            )).scalar() or 0
            incident_ok = incident_count > 0 or completed == 0
            stage6 = self._record_stage("Incident System", incident_ok, time.time() - t0)
            stages.append(stage6)

            t0 = time.time()
            try:
                from shared.notify import _enabled
                notify_ok = _enabled
            except Exception:
                notify_ok = False
            stage7 = self._record_stage("Notifications", notify_ok, time.time() - t0)
            stages.append(stage7)
            if not notify_ok:
                warnings.append("Notifications: Telegram not configured")

        self.add_evidence("pipeline_stages", stages)
        metrics["stages_total"] = len(stages)
        metrics["stages_passed"] = sum(1 for s in stages if s["passed"])
        metrics["stages"] = {s["name"]: s["passed"] for s in stages}

        first_failure_idx = next((i for i, s in enumerate(stages) if not s["passed"]), -1)
        first_failure_name = stages[first_failure_idx]["name"] if first_failure_idx >= 0 else None

        status = "PASS" if first_failure_idx < 0 else ("WARNING" if not failures else "FAIL")
        summary = (
            f"Pipeline: {metrics['stages_passed']}/{len(stages)} stages passed."
        )
        if first_failure_name:
            summary += f" First failure: {first_failure_name}."

        return self._build_report(
            status=status,
            summary=summary,
            failures=failures,
            warnings=warnings,
            metrics=metrics,
        )

    def _record_stage(self, name: str, passed: bool, duration: float) -> dict:
        return {
            "name": name,
            "passed": passed,
            "duration_ms": round(duration * 1000, 1),
            "status": "PASS" if passed else "FAIL",
        }
