"""Base verifier class with evidence collection."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any

from verification.models import Evidence, VerificationReport


class BaseVerifier:
    verification_type: str = "base"

    def __init__(self) -> None:
        self.evidence: list[Evidence] = []

    def add_evidence(self, key: str, value: Any, description: str = "") -> None:
        self.evidence.append(Evidence(key=key, value=value, description=description))

    def verify(self) -> VerificationReport:
        raise NotImplementedError

    def _build_report(
        self,
        status: str,
        summary: str,
        failures: list[str] | None = None,
        warnings: list[str] | None = None,
        metrics: dict[str, Any] | None = None,
        recommendations: list[str] | None = None,
    ) -> VerificationReport:
        now = datetime.now(timezone.utc)
        duration = time.time() - self._start_time if hasattr(self, "_start_time") else 0.0
        return VerificationReport(
            verification_id=uuid.uuid4().hex[:12],
            verification_type=self.verification_type,
            started_at=getattr(self, "_started", now),
            completed_at=now,
            duration=round(duration, 3),
            status=status,
            summary=summary,
            failures=failures or [],
            warnings=warnings or [],
            metrics=metrics or {},
            recommendations=recommendations or [],
            evidence=self.evidence.copy(),
        )

    def run(self) -> VerificationReport:
        self.evidence = []
        self._started = datetime.now(timezone.utc)
        self._start_time = time.time()
        try:
            return self.verify()
        except Exception as exc:
            elapsed = time.time() - self._start_time
            return VerificationReport(
                verification_id=uuid.uuid4().hex[:12],
                verification_type=self.verification_type,
                started_at=self._started,
                completed_at=datetime.now(timezone.utc),
                duration=round(elapsed, 3),
                status="FAIL",
                summary=f"Verification raised an exception: {exc}",
                failures=[str(exc)],
                recommendations=["Investigate the exception traceback in logs."],
                evidence=self.evidence.copy(),
            )
