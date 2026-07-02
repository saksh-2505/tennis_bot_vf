"""Verification dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Evidence:
    key: str
    value: Any
    description: str = ""


@dataclass
class VerificationReport:
    verification_id: str
    verification_type: str
    started_at: datetime
    completed_at: datetime
    duration: float
    status: str  # PASS, WARNING, FAIL
    summary: str
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verification_id": self.verification_id,
            "verification_type": self.verification_type,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration": self.duration,
            "status": self.status,
            "summary": self.summary,
            "failures": self.failures,
            "warnings": self.warnings,
            "metrics": self.metrics,
            "recommendations": self.recommendations,
            "evidence": [
                {"key": e.key, "value": e.value, "description": e.description}
                for e in self.evidence
            ],
        }

    def is_healthy(self) -> bool:
        return self.status == "PASS"


@dataclass
class HealthScore:
    score: int  # 0–100
    factors: dict[str, float] = field(default_factory=dict)
    trend: list[dict[str, Any]] = field(default_factory=list)
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "factors": self.factors,
            "trend": self.trend,
            "calculated_at": self.calculated_at.isoformat(),
        }


@dataclass
class DailyReport:
    date: str
    platform_health_score: int
    infrastructure_status: str
    collection_health: str
    database_health: str
    pipeline_health: str
    completed_matches: int
    incident_summary: dict[str, int]
    verification_summary: dict[str, str]
    historical_trend: list[int]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "platform_health_score": self.platform_health_score,
            "infrastructure_status": self.infrastructure_status,
            "collection_health": self.collection_health,
            "database_health": self.database_health,
            "pipeline_health": self.pipeline_health,
            "completed_matches": self.completed_matches,
            "incident_summary": self.incident_summary,
            "verification_summary": self.verification_summary,
            "historical_trend": self.historical_trend,
            "generated_at": self.generated_at.isoformat(),
        }
