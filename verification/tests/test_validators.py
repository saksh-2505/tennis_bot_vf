"""Tests for verification validators."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from verification.validators.infrastructure import InfrastructureVerifier
from verification.validators.database import DatabaseVerifier
from verification.validators.collection import CollectionVerifier
from verification.validators.pipeline import PipelineVerifier


class TestInfrastructureVerifier:
    def test_creates_report(self) -> None:
        verifier = InfrastructureVerifier()
        with patch.object(verifier, "_check_postgresql"), \
             patch.object(verifier, "_check_timescaledb"), \
             patch.object(verifier, "_check_docker"), \
             patch.object(verifier, "_check_disk"), \
             patch.object(verifier, "_check_memory"), \
             patch.object(verifier, "_check_cpu"), \
             patch.object(verifier, "_check_internet"), \
             patch.object(verifier, "_check_dns"), \
             patch.object(verifier, "_check_time_sync"):
            report = verifier.run()
            assert report.verification_type == "infrastructure"
            assert report.status in ("PASS", "WARNING", "FAIL")


class TestDatabaseVerifier:
    def test_creates_report(self) -> None:
        verifier = DatabaseVerifier()
        report = verifier.run()
        assert report.verification_type == "database"
        assert report.status in ("PASS", "WARNING", "FAIL")


class TestCollectionVerifier:
    def test_creates_report(self) -> None:
        verifier = CollectionVerifier()
        report = verifier.run()
        assert report.verification_type == "collection"
        assert report.status in ("PASS", "WARNING", "FAIL")


class TestPipelineVerifier:
    def test_creates_report(self) -> None:
        verifier = PipelineVerifier()
        report = verifier.run()
        assert report.verification_type == "pipeline"
        assert report.status in ("PASS", "WARNING", "FAIL")


class TestVerificationAPI:
    def test_verify_platform_returns_list(self) -> None:
        from verification.api import verify_platform
        reports = verify_platform()
        assert isinstance(reports, list)
        assert len(reports) == 9
        for r in reports:
            assert r.status in ("PASS", "WARNING", "FAIL")

    def test_verify_single_suites(self) -> None:
        from verification.api import (
            verify_collection, verify_database, verify_infrastructure,
            verify_pipeline, verify_dataset,
        )
        with (
            patch.object(InfrastructureVerifier, "_check_postgresql"),
            patch.object(InfrastructureVerifier, "_check_timescaledb"),
            patch.object(InfrastructureVerifier, "_check_docker"),
            patch.object(InfrastructureVerifier, "_check_disk"),
            patch.object(InfrastructureVerifier, "_check_memory"),
            patch.object(InfrastructureVerifier, "_check_cpu"),
            patch.object(InfrastructureVerifier, "_check_internet"),
            patch.object(InfrastructureVerifier, "_check_dns"),
            patch.object(InfrastructureVerifier, "_check_time_sync"),
        ):
            for fn in [verify_collection, verify_database, verify_infrastructure,
                       verify_pipeline, verify_dataset]:
                report = fn()
                assert report.status in ("PASS", "WARNING", "FAIL")


class TestReportStorage:
    def test_save_and_load(self, tmp_path) -> None:
        from unittest.mock import patch as mp
        from verification.models import VerificationReport

        now = datetime.now(timezone.utc)
        report = VerificationReport(
            verification_id="test123",
            verification_type="collection",
            started_at=now,
            completed_at=now,
            duration=0.5,
            status="PASS",
            summary="All good",
            metrics={"count": 5},
        )

        with mp("verification.reports.storage.REPORTS_DIR", str(tmp_path)):
            from verification.reports.storage import ReportStorage
            storage = ReportStorage()
            filepath = storage.save(report)
            assert filepath.endswith(".json")

            loaded = storage.load_latest()
            assert loaded is not None
            assert loaded["verification_type"] == "collection"
            assert loaded["status"] == "PASS"


class TestDailyReport:
    def test_generate_daily_report(self) -> None:
        from verification.reports.generator import generate_daily_report

        with patch("verification.reports.generator.HealthScoreEngine") as mock_engine:
            mock_score = MagicMock()
            mock_score.score = 85
            mock_score.trend = [{"score": 80}]
            mock_engine.return_value.calculate.return_value = mock_score

            with patch("verification.reports.generator.PlatformDoctor") as mock_doctor:
                mock_doctor.return_value.examine.return_value = {
                    "results": [
                        {"name": "Infrastructure", "status": "PASS"},
                        {"name": "Collection", "status": "PASS"},
                        {"name": "Database", "status": "PASS"},
                        {"name": "Pipelines", "status": "PASS"},
                    ],
                }

                report = generate_daily_report()
                assert report.platform_health_score == 85
                assert report.infrastructure_status == "PASS"
