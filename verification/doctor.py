"""Platform Doctor.

CLI-friendly health overview that runs all verification suites and
prints a summary report.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from verification.validators.collection import CollectionVerifier
from verification.validators.database import DatabaseVerifier
from verification.validators.finalizer import FinalizerVerifier
from verification.validators.incident import IncidentVerifier
from verification.validators.infrastructure import InfrastructureVerifier
from verification.validators.notification import NotificationVerifier
from verification.validators.pipeline import PipelineVerifier
from verification.validators.registry import RegistryVerifier
from verification.models import VerificationReport


class PlatformDoctor:
    def __init__(self) -> None:
        self.reports: dict[str, VerificationReport] = {}
        self._verifiers: dict[str, object] = {
            "Infrastructure": InfrastructureVerifier,
            "Discovery": __import__("verification.validators.discovery", fromlist=["DiscoveryVerifier"]).DiscoveryVerifier,
            "Registry": RegistryVerifier,
            "Collection": CollectionVerifier,
            "Database": DatabaseVerifier,
            "Finalizer": FinalizerVerifier,
            "Incidents": IncidentVerifier,
            "Notifications": NotificationVerifier,
            "Pipelines": PipelineVerifier,
        }

    def examine(self) -> dict[str, Any]:
        self.reports = {}
        results: list[dict] = []
        overall_healthy = True

        for name, verifier_cls in self._verifiers.items():
            verifier = verifier_cls()
            report = verifier.run()
            self.reports[name] = report
            results.append({
                "name": name,
                "status": report.status,
                "summary": report.summary,
                "duration": report.duration,
            })
            if report.status == "FAIL":
                overall_healthy = False

        return {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "results": results,
            "overall_healthy": overall_healthy,
            "total_suites": len(results),
            "passed": sum(1 for r in results if r["status"] == "PASS"),
            "warnings": sum(1 for r in results if r["status"] == "WARNING"),
            "failed": sum(1 for r in results if r["status"] == "FAIL"),
        }

    def print_report(self) -> str:
        result = self.examine()
        lines = ["Platform Doctor", "=" * 60]
        for r in result["results"]:
            icon = {"PASS": "✓", "WARNING": "⚠", "FAIL": "✗"}.get(r["status"], "?")
            lines.append(f"  {icon} {r['name']:<20} {r['status']:<10} {r['summary']}")
        lines.append("=" * 60)
        lines.append(
            f"Verification: {'PASS' if result['overall_healthy'] else 'FAIL'}  "
            f"({result['passed']} pass, {result['warnings']} warn, {result['failed']} fail)"
        )
        return "\n".join(lines)

    def get_overall_health_pct(self) -> int:
        result = self.examine()
        total = result["total_suites"] or 1
        passed = result["passed"]
        warnings = result["warnings"]
        score = int((passed + warnings * 0.5) / total * 100)
        return min(100, max(0, score))
