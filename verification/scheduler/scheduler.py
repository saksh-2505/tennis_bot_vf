"""Verification Scheduler.

Run verification suites on schedule:
- Infrastructure: every 1 minute
- Collection: every 5 minutes
- Database: every 15 minutes
- Dataset: after every completed match
- Platform Doctor: daily
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone

from verification.api import (
    verify_collection,
    verify_database,
    verify_infrastructure,
    verify_platform,
    verify_pipeline,
)
from verification.doctor import PlatformDoctor
from verification.health_score import HealthScoreEngine
from verification.reports.storage import ReportStorage


class VerificationScheduler:
    def __init__(self, check_interval: float = 1.0) -> None:
        self._running = False
        self._tasks: dict[str, dict] = {
            "infrastructure": {"interval": 60, "last_run": 0, "fn": self._run_infrastructure},
            "collection": {"interval": 300, "last_run": 0, "fn": self._run_collection},
            "database": {"interval": 900, "last_run": 0, "fn": self._run_database},
            "platform_doctor": {"interval": 86400, "last_run": 0, "fn": self._run_platform_doctor},
        }
        self._check_interval = check_interval
        self.storage = ReportStorage()
        self._score_engine = HealthScoreEngine()

    async def start(self) -> None:
        self._running = True
        while self._running:
            now = time.time()
            for name, task in self._tasks.items():
                if now - task["last_run"] >= task["interval"]:
                    await task["fn"]()
                    task["last_run"] = now
            await asyncio.sleep(self._check_interval)

    def stop(self) -> None:
        self._running = False

    async def _run_infrastructure(self) -> None:
        report = verify_infrastructure()
        self.storage.save(report)

    async def _run_collection(self) -> None:
        report = verify_collection()
        self.storage.save(report)

    async def _run_database(self) -> None:
        report = verify_database()
        self.storage.save(report)
        verify_pipeline()

    async def _run_platform_doctor(self) -> None:
        doctor = PlatformDoctor()
        report_text = doctor.print_report()
        score = self._score_engine.calculate()

        daily_file = os.path.join(
            os.path.dirname(__file__), "reports", "archive",
            f"daily_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json",
        )
        os.makedirs(os.path.dirname(daily_file), exist_ok=True)
        with open(daily_file, "w") as f:
            json.dump({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "score": score.to_dict(),
                "doctor_output": report_text,
            }, f, indent=2)
