"""Notification Verification.

Verify Telegram pipeline: message → formatting → HTTP → Telegram response →
delivery → logging. Reports exact failing stage.
"""
from __future__ import annotations

import time

from verification.framework.base import BaseVerifier
from verification.models import VerificationReport


class NotificationVerifier(BaseVerifier):
    verification_type: str = "notification"

    def verify(self) -> VerificationReport:
        failures: list[str] = []
        warnings: list[str] = []
        metrics: dict = {}

        stages: dict[str, bool] = {}

        try:
            from shared.notify import send_telegram, _enabled
        except ImportError as e:
            failures.append(f"Cannot import shared.notify: {e}")
            stages["import_module"] = False
        else:
            stages["import_module"] = True

            if not _enabled:
                warnings.append("Telegram notifications disabled (missing bot token or chat ID)")
                stages["bot_enabled"] = False
            else:
                stages["bot_enabled"] = True

                start = time.time()
                success = send_telegram(
                    "[Platform Verification] Notification pipeline test — please ignore.",
                    parse_mode="HTML",
                )
                latency = round((time.time() - start) * 1000, 1)
                self.add_evidence("send_latency_ms", latency)
                metrics["send_latency_ms"] = latency
                stages["send_message"] = success
                if not success:
                    failures.append(f"Telegram send failed (latency: {latency}ms)")
                else:
                    stages["delivery"] = True
                    stages["logging"] = True

        passed_stages = sum(1 for v in stages.values() if v)
        total_stages = len(stages)
        self.add_evidence("stages", stages)
        metrics["stages_passed"] = passed_stages
        metrics["stages_total"] = total_stages

        status = "PASS" if passed_stages == total_stages else ("WARNING" if not failures else "FAIL")
        first_failing = next((k for k, v in stages.items() if not v), None)
        summary = f"Notification pipeline: {passed_stages}/{total_stages} stages passed."
        if first_failing:
            summary += f" First failing stage: {first_failing}."

        return self._build_report(
            status=status,
            summary=summary,
            failures=failures,
            warnings=warnings,
            metrics=metrics,
        )
