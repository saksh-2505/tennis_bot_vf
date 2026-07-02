"""Verification API.

Expose: verify_platform(), verify_collection(), verify_database(),
verify_dataset(), verify_pipeline(), verify_notifications(),
verify_incidents(), platform_doctor(), generate_daily_report(),
get_latest_health_score().
"""
from __future__ import annotations

from verification.doctor import PlatformDoctor
from verification.health_score import HealthScoreEngine
from verification.models import DailyReport, HealthScore, VerificationReport
from verification.validators.collection import CollectionVerifier
from verification.validators.database import DatabaseVerifier
from verification.validators.dataset import DatasetVerifier
from verification.validators.discovery import DiscoveryVerifier
from verification.validators.finalizer import FinalizerVerifier
from verification.validators.incident import IncidentVerifier
from verification.validators.infrastructure import InfrastructureVerifier
from verification.validators.notification import NotificationVerifier
from verification.validators.pipeline import PipelineVerifier
from verification.validators.registry import RegistryVerifier


def verify_infrastructure() -> VerificationReport:
    return InfrastructureVerifier().run()


def verify_discovery() -> VerificationReport:
    return DiscoveryVerifier().run()


def verify_registry() -> VerificationReport:
    return RegistryVerifier().run()


def verify_collection() -> VerificationReport:
    return CollectionVerifier().run()


def verify_database() -> VerificationReport:
    return DatabaseVerifier().run()


def verify_finalizer() -> VerificationReport:
    return FinalizerVerifier().run()


def verify_dataset() -> VerificationReport:
    return DatasetVerifier().run()


def verify_incidents() -> VerificationReport:
    return IncidentVerifier().run()


def verify_notifications() -> VerificationReport:
    return NotificationVerifier().run()


def verify_pipeline() -> VerificationReport:
    return PipelineVerifier().run()


def verify_platform() -> list[VerificationReport]:
    verifiers = [
        InfrastructureVerifier(),
        DiscoveryVerifier(),
        RegistryVerifier(),
        CollectionVerifier(),
        DatabaseVerifier(),
        FinalizerVerifier(),
        IncidentVerifier(),
        NotificationVerifier(),
        PipelineVerifier(),
    ]
    return [v.run() for v in verifiers]


def platform_doctor() -> dict:
    return PlatformDoctor().examine()


def get_latest_health_score() -> HealthScore | None:
    return HealthScoreEngine().calculate()


def generate_daily_report() -> DailyReport:
    from datetime import datetime, timezone

    doctor = PlatformDoctor()
    result = doctor.examine()
    score = HealthScoreEngine().calculate()

    incident_summary = {}
    for r in result["results"]:
        if r["name"] == "Incidents":
            incident_summary = r

    verification_summary = {
        r["name"]: r["status"] for r in result["results"]
    }

    return DailyReport(
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        platform_health_score=score.score,
        infrastructure_status=verification_summary.get("Infrastructure", "UNKNOWN"),
        collection_health=verification_summary.get("Collection", "UNKNOWN"),
        database_health=verification_summary.get("Database", "UNKNOWN"),
        pipeline_health=verification_summary.get("Pipelines", "UNKNOWN"),
        completed_matches=0,
        incident_summary={},
        verification_summary=verification_summary,
        historical_trend=[e["score"] for e in score.trend] if score.trend else [],
    )
