"""Daily Verification Report.

Automatically generates a daily platform report with:
Infrastructure, Collector Health, Database Health, Pipeline Health,
Completed Matches, Incident Summary, Verification Summary,
Platform Health Score, Historical Trend.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from verification.api import verify_platform
from verification.doctor import PlatformDoctor
from verification.health_score import HealthScoreEngine
from verification.models import DailyReport


def generate_daily_report() -> DailyReport:
    doctor = PlatformDoctor()
    result = doctor.examine()
    score = HealthScoreEngine().calculate()

    verification_summary = {r["name"]: r["status"] for r in result["results"]}

    infrastructure_status = verification_summary.get("Infrastructure", "UNKNOWN")
    collection_health = verification_summary.get("Collection", "UNKNOWN")
    database_health = verification_summary.get("Database", "UNKNOWN")
    pipeline_health = verification_summary.get("Pipelines", "UNKNOWN")

    completed_matches = 0
    try:
        from database import SessionLocal
        from sqlalchemy import text
        with SessionLocal() as session:
            completed_matches = session.execute(text(
                "SELECT COUNT(*) FROM completed_matches"
            )).scalar() or 0
    except Exception:
        pass

    incident_summary: dict[str, int] = {}
    try:
        from database import SessionLocal
        from sqlalchemy import text
        with SessionLocal() as session:
            open_incidents = session.execute(text(
                "SELECT COUNT(*) FROM incidents WHERE status IN ('OPEN', 'ACKNOWLEDGED')"
            )).scalar() or 0
            total_incidents = session.execute(text(
                "SELECT COUNT(*) FROM incidents"
            )).scalar() or 0
            incident_summary = {
                "open": open_incidents,
                "total": total_incidents,
            }
    except Exception:
        pass

    trend = [e["score"] for e in score.trend] if score.trend else []

    return DailyReport(
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        platform_health_score=score.score,
        infrastructure_status=infrastructure_status,
        collection_health=collection_health,
        database_health=database_health,
        pipeline_health=pipeline_health,
        completed_matches=completed_matches,
        incident_summary=incident_summary,
        verification_summary=verification_summary,
        historical_trend=trend,
    )


def save_daily_report(report: DailyReport) -> str:
    out_dir = os.path.join(os.path.dirname(__file__), "archive")
    os.makedirs(out_dir, exist_ok=True)
    filename = f"daily_{report.date}.json"
    filepath = os.path.join(out_dir, filename)
    with open(filepath, "w") as f:
        json.dump(report.to_dict(), f, indent=2)
    return filepath
