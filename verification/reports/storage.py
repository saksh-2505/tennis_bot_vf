"""Verification report generation and storage."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from verification.models import VerificationReport


REPORTS_DIR = os.path.join(os.path.dirname(__file__), "archive")


class ReportStorage:
    def __init__(self) -> None:
        os.makedirs(REPORTS_DIR, exist_ok=True)

    def save(self, report: VerificationReport) -> str:
        filename = (
            f"{report.verification_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            f"_{report.verification_id}.json"
        )
        filepath = os.path.join(REPORTS_DIR, filename)
        with open(filepath, "w") as f:
            json.dump(report.to_dict(), f, indent=2)
        return filepath

    def load_all(self, limit: int = 100) -> list[dict[str, Any]]:
        if not os.path.exists(REPORTS_DIR):
            return []
        reports: list[dict] = []
        for fname in sorted(os.listdir(REPORTS_DIR), reverse=True):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(REPORTS_DIR, fname)
            try:
                with open(fpath) as f:
                    reports.append(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass
            if len(reports) >= limit:
                break
        return reports

    def load_latest(self, verification_type: str | None = None) -> dict | None:
        reports = self.load_all(limit=200)
        for r in reports:
            if verification_type and r.get("verification_type") != verification_type:
                continue
            return r
        return None

    def get_verification_history(self, days: int = 7) -> list[dict[str, Any]]:
        return self.load_all(limit=500)
