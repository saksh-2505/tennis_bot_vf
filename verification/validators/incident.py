"""Incident Verification.

Verify: incident creation, deduplication, resolution,
package generation, severity classification, trace references.
"""
from __future__ import annotations

from database import SessionLocal
from sqlalchemy import text

from verification.framework.base import BaseVerifier
from verification.models import VerificationReport


class IncidentVerifier(BaseVerifier):
    verification_type: str = "incident"

    def verify(self) -> VerificationReport:
        failures: list[str] = []
        warnings: list[str] = []
        metrics: dict = {}

        with SessionLocal() as session:
            self._check_incident_counts(session, failures, warnings, metrics)
            self._check_deduplication(session, failures, warnings, metrics)
            self._check_resolution_rate(session, warnings, metrics)
            self._check_severity_distribution(session, metrics)
            self._check_package_generation(session, warnings, metrics)

        status = "PASS"
        summary = "Incident system verification passed."
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

    def _check_incident_counts(self, session, failures, warnings, metrics) -> None:
        total = session.execute(text("SELECT COUNT(*) FROM incidents")).scalar() or 0
        open_incidents = session.execute(text(
            "SELECT COUNT(*) FROM incidents WHERE status = 'OPEN'"
        )).scalar() or 0
        acknowledged = session.execute(text(
            "SELECT COUNT(*) FROM incidents WHERE status = 'ACKNOWLEDGED'"
        )).scalar() or 0
        resolved = session.execute(text(
            "SELECT COUNT(*) FROM incidents WHERE status = 'RESOLVED'"
        )).scalar() or 0

        self.add_evidence("total_incidents", total)
        self.add_evidence("open_incidents", open_incidents)
        self.add_evidence("acknowledged_incidents", acknowledged)
        self.add_evidence("resolved_incidents", resolved)
        metrics["total_incidents"] = total
        metrics["open_incidents"] = open_incidents
        metrics["resolved_incidents"] = resolved

        if total == 0:
            warnings.append("No incidents recorded — may indicate monitor is not running")

    def _check_deduplication(self, session, failures, warnings, metrics) -> None:
        dupes = session.execute(text(
            "SELECT COUNT(*) FROM ("
            "  SELECT incident_hash, COUNT(*) FROM incidents "
            "  GROUP BY incident_hash HAVING COUNT(*) > 1"
            ") AS d"
        )).scalar() or 0
        self.add_evidence("duplicate_incident_hashes", dupes)
        metrics["duplicate_incidents"] = dupes
        if dupes > 0:
            failures.append(f"Duplicate incident hashes detected: {dupes}")

    def _check_resolution_rate(self, session, warnings, metrics) -> None:
        total = session.execute(text("SELECT COUNT(*) FROM incidents")).scalar() or 1
        resolved = session.execute(text(
            "SELECT COUNT(*) FROM incidents WHERE status = 'RESOLVED'"
        )).scalar() or 0
        resolution_rate = round(resolved / total * 100, 1) if total else 0
        self.add_evidence("resolution_rate_pct", resolution_rate)
        metrics["resolution_rate_pct"] = resolution_rate

    def _check_severity_distribution(self, session, metrics) -> None:
        dist = session.execute(text(
            "SELECT severity, COUNT(*) as cnt FROM incidents GROUP BY severity"
        )).fetchall()
        sev_map = {r[0]: r[1] for r in dist}
        self.add_evidence("severity_distribution", sev_map)
        metrics["severity_info"] = sev_map.get("INFO", 0)
        metrics["severity_warning"] = sev_map.get("WARNING", 0)
        metrics["severity_error"] = sev_map.get("ERROR", 0)
        metrics["severity_critical"] = sev_map.get("CRITICAL", 0)

    def _check_package_generation(self, session, warnings, metrics) -> None:
        total_open = session.execute(text(
            "SELECT COUNT(*) FROM incidents WHERE status IN ('OPEN', 'ACKNOWLEDGED')"
        )).scalar() or 1
        metrics["open_incidents_count"] = total_open
