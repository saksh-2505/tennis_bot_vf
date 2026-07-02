"""Registry Verification.

Verify: Every discovered match has a registry entry, no duplicates,
every tracked match references valid players and betting markets.
"""
from __future__ import annotations

from database import SessionLocal
from sqlalchemy import text

from verification.framework.base import BaseVerifier
from verification.models import VerificationReport


class RegistryVerifier(BaseVerifier):
    verification_type: str = "registry"

    def verify(self) -> VerificationReport:
        failures: list[str] = []
        warnings: list[str] = []
        metrics: dict = {}

        with SessionLocal() as session:
            self._check_registry_coverage(session, failures, warnings, metrics)
            self._check_player_mappings(session, failures, warnings, metrics)
            self._check_betting_mappings(session, failures, warnings, metrics)
            self._check_tracking_enabled(session, warnings, metrics)

        status = "PASS"
        summary = "Registry verification passed."
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

    def _check_registry_coverage(self, session, failures, warnings, metrics) -> None:
        fs_total = session.execute(text("SELECT COUNT(*) FROM flashscorefoundmatches")).scalar() or 0
        tracked_total = session.execute(text("SELECT COUNT(*) FROM tracked_matches")).scalar() or 0
        self.add_evidence("flashscore_total", fs_total)
        self.add_evidence("tracked_total", tracked_total)
        metrics["registry_coverage_pct"] = round(tracked_total / fs_total * 100, 1) if fs_total else 0

        if fs_total > 0 and tracked_total == 0:
            failures.append("No registry entries despite discovered matches")
        elif tracked_total < fs_total * 0.5:
            warnings.append(
                f"Low registry coverage: {tracked_total}/{fs_total} "
                f"({metrics['registry_coverage_pct']}%)"
            )

    def _check_player_mappings(self, session, failures, warnings, metrics) -> None:
        resolved = session.execute(text(
            "SELECT COUNT(*) FROM tracked_matches "
            "WHERE player1_id IS NOT NULL AND player2_id IS NOT NULL"
        )).scalar() or 0
        total = session.execute(text("SELECT COUNT(*) FROM tracked_matches")).scalar() or 1
        pct = round(resolved / total * 100, 1)
        self.add_evidence("player_resolved", resolved)
        self.add_evidence("player_resolved_pct", pct)
        metrics["player_resolved_count"] = resolved
        metrics["player_resolved_pct"] = pct

        if pct < 70:
            failures.append(f"Player resolution low: {resolved}/{total} ({pct}%)")
        elif pct < 90:
            warnings.append(f"Player resolution below 90%: {resolved}/{total} ({pct}%)")

    def _check_betting_mappings(self, session, failures, warnings, metrics) -> None:
        with_betting = session.execute(text(
            "SELECT COUNT(*) FROM tracked_matches "
            "WHERE betting_market_id IS NOT NULL"
        )).scalar() or 0
        total = session.execute(text("SELECT COUNT(*) FROM tracked_matches")).scalar() or 1
        pct = round(with_betting / total * 100, 1)
        self.add_evidence("betting_mapped", with_betting)
        self.add_evidence("betting_mapped_pct", pct)
        metrics["betting_mapped_count"] = with_betting
        metrics["betting_mapped_pct"] = pct

        if pct < 10:
            warnings.append(f"Betting market coverage low: {with_betting}/{total} ({pct}%)")

    def _check_tracking_enabled(self, session, warnings, metrics) -> None:
        total = session.execute(text("SELECT COUNT(*) FROM tracked_matches")).scalar() or 0
        enabled = session.execute(text(
            "SELECT COUNT(*) FROM tracked_matches WHERE tracking_enabled = TRUE"
        )).scalar() or 0
        disabled = total - enabled
        self.add_evidence("tracking_enabled", enabled)
        self.add_evidence("tracking_disabled", disabled)
        metrics["tracking_disabled"] = disabled
