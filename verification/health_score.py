"""Health Score Engine.

Calculates Platform Health Score 0-100 from weighted subsystems:
Infrastructure, Collectors, Database, Pipelines, Incidents, Dataset Quality, Finalization.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, date
from typing import Any

from verification.doctor import PlatformDoctor
from verification.models import HealthScore


SCORE_HISTORY_FILE = os.path.join(
    os.path.dirname(__file__), "reports", "archive", "score_history.jsonl"
)


class HealthScoreEngine:
    def __init__(self) -> None:
        self._doctor = PlatformDoctor()

    def calculate(self) -> HealthScore:
        result = self._doctor.examine()

        weights: dict[str, float] = {
            "Infrastructure": 15,
            "Collection": 20,
            "Database": 15,
            "Pipelines": 15,
            "Finalizer": 10,
            "Registry": 8,
            "Discovery": 7,
            "Incidents": 5,
            "Notifications": 5,
        }

        factors: dict[str, float] = {}
        total_score = 0.0

        for r in result["results"]:
            name = r["name"]
            w = weights.get(name, 5)
            status_score = {"PASS": 1.0, "WARNING": 0.5, "FAIL": 0.0}.get(r["status"], 0)
            component = w * status_score
            factors[name] = component
            total_score += component

        max_possible = sum(weights.get(r["name"], 5) for r in result["results"])
        score = int((total_score / max_possible) * 100) if max_possible else 0

        trend = self._load_trend()
        trend.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "score": score,
        })
        trend = trend[-30:]  # keep last 30
        self._save_trend(trend)

        return HealthScore(
            score=score,
            factors=factors,
            trend=trend,
            calculated_at=datetime.now(timezone.utc),
        )

    def get_latest(self) -> HealthScore | None:
        trend = self._load_trend()
        if not trend:
            return None
        latest = trend[-1]
        return HealthScore(
            score=latest["score"],
            trend=trend,
            calculated_at=datetime.fromisoformat(latest["timestamp"]),
        )

    def get_history(self, days: int = 7) -> list[dict[str, Any]]:
        return self._load_trend()[-days:]

    def _load_trend(self) -> list[dict[str, Any]]:
        os.makedirs(os.path.dirname(SCORE_HISTORY_FILE), exist_ok=True)
        if not os.path.exists(SCORE_HISTORY_FILE):
            return []
        entries: list[dict] = []
        with open(SCORE_HISTORY_FILE) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries

    def _save_trend(self, trend: list[dict]) -> None:
        os.makedirs(os.path.dirname(SCORE_HISTORY_FILE), exist_ok=True)
        with open(SCORE_HISTORY_FILE, "w") as f:
            for entry in trend:
                f.write(json.dumps(entry) + "\n")
