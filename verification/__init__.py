"""Platform Verification Framework.

Answers: "Can I prove the platform is healthy?" with evidence-based verification.

Key API:
- verify_platform()          — run all verification suites
- verify_infrastructure()    — VM, Docker, DB connectivity
- verify_collection()        — live match data quality
- verify_database()          — FK integrity, orphans, hypertables
- verify_pipeline()          — end-to-end pipeline stages
- platform_doctor()          — CLI-friendly health overview
- generate_daily_report()    — daily platform summary
- get_latest_health_score()  — 0-100 score
"""

from verification.api import (
    generate_daily_report,
    get_latest_health_score,
    platform_doctor,
    verify_collection,
    verify_database,
    verify_dataset,
    verify_incidents,
    verify_infrastructure,
    verify_notifications,
    verify_pipeline,
    verify_platform,
)
from verification.doctor import PlatformDoctor
from verification.health_score import HealthScoreEngine
from verification.models import DailyReport, Evidence, HealthScore, VerificationReport

__all__ = [
    "verify_platform",
    "verify_infrastructure",
    "verify_collection",
    "verify_database",
    "verify_dataset",
    "verify_pipeline",
    "verify_notifications",
    "verify_incidents",
    "platform_doctor",
    "generate_daily_report",
    "get_latest_health_score",
    "VerificationReport",
    "HealthScore",
    "DailyReport",
    "Evidence",
    "PlatformDoctor",
    "HealthScoreEngine",
]
