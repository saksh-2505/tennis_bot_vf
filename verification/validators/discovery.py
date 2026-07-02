"""Discovery Verification.

Verify: Flashscore and betting site discovery health — expected matches found,
no duplicates, player/betting mapping quality, tournament coverage.
"""
from __future__ import annotations

from database import SessionLocal
from sqlalchemy import text

from verification.framework.base import BaseVerifier
from verification.models import VerificationReport


class DiscoveryVerifier(BaseVerifier):
    verification_type: str = "discovery"

    def verify(self) -> VerificationReport:
        failures: list[str] = []
        warnings: list[str] = []
        metrics: dict = {}

        with SessionLocal() as session:
            self._check_flashscore_discovery(session, failures, warnings, metrics)
            self._check_betting_discovery(session, failures, warnings, metrics)
            self._check_tournament_coverage(session, failures, warnings, metrics)

        status = "PASS"
        summary = "Discovery verification passed."
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

    def _check_flashscore_discovery(self, session, failures, warnings, metrics) -> None:
        fs_count = session.execute(text("SELECT COUNT(*) FROM flashscorefoundmatches")).scalar() or 0
        self.add_evidence("flashscore_discovered", fs_count)
        metrics["flashscore_match_count"] = fs_count

        if fs_count == 0:
            failures.append("Flashscore discovery: 0 matches discovered")
        elif fs_count < 5:
            warnings.append(f"Flashscore discovery: only {fs_count} matches")

        dupes = session.execute(text(
            "SELECT COUNT(*) FROM ("
            "  SELECT flashscore_match_id, COUNT(*) FROM flashscorefoundmatches "
            "  GROUP BY flashscore_match_id HAVING COUNT(*) > 1"
            ") AS d"
        )).scalar() or 0
        if dupes > 0:
            failures.append(f"Flashscore: {dupes} duplicate match IDs")
        metrics["flashscore_duplicates"] = dupes

    def _check_betting_discovery(self, session, failures, warnings, metrics) -> None:
        bt_count = session.execute(text("SELECT COUNT(*) FROM bettingsitefoundmatches")).scalar() or 0
        self.add_evidence("betting_discovered", bt_count)
        metrics["betting_match_count"] = bt_count

        if bt_count == 0:
            warnings.append("Betting discovery: 0 markets discovered")
        elif bt_count < 5:
            warnings.append(f"Betting discovery: only {bt_count} markets")

        dupes = session.execute(text(
            "SELECT COUNT(*) FROM ("
            "  SELECT market_id, COUNT(*) FROM bettingsitefoundmatches "
            "  GROUP BY market_id HAVING COUNT(*) > 1"
            ") AS d"
        )).scalar() or 0
        if dupes > 0:
            failures.append(f"Betting: {dupes} duplicate market IDs")
        metrics["betting_duplicates"] = dupes

    def _check_tournament_coverage(self, session, failures, warnings, metrics) -> None:
        tournaments = session.execute(text(
            "SELECT tournament, COUNT(*) as cnt FROM tracked_matches "
            "WHERE status IN ('DISCOVERED', 'SCHEDULED', 'LIVE') "
            "GROUP BY tournament ORDER BY cnt DESC"
        )).fetchall()
        self.add_evidence("active_tournaments", [dict(r._mapping) for r in tournaments])
        metrics["active_tournament_count"] = len(tournaments)
