"""Tests for Platform Doctor and Health Score."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from verification.doctor import PlatformDoctor
from verification.health_score import HealthScoreEngine


def test_platform_doctor_examine_calls_all_verifiers() -> None:
    doctor = PlatformDoctor()

    with patch.object(
        doctor, "_verifiers", {k: MagicMock() for k in doctor._verifiers}
    ):
        for cls in doctor._verifiers.values():
            mock_v = MagicMock()
            mock_v.run.return_value.status = "PASS"
            mock_v.run.return_value.summary = "ok"
            mock_v.run.return_value.duration = 0.1
            cls.return_value = mock_v

        result = doctor.examine()

        assert "results" in result
        assert result["overall_healthy"] is True
        assert len(result["results"]) == len(doctor._verifiers)


def test_platform_doctor_print_report() -> None:
    doctor = PlatformDoctor()
    with patch.object(
        doctor, "_verifiers", {k: MagicMock() for k in doctor._verifiers}
    ):
        for cls in doctor._verifiers.values():
            mock_v = MagicMock()
            run_result = MagicMock()
            run_result.status = "PASS"
            run_result.summary = "ok"
            run_result.duration = 0.1
            mock_v.run.return_value = run_result
            cls.return_value = mock_v

        output = doctor.print_report()
        assert "Platform Doctor" in output
        assert "✓" in output


def test_health_score_engine_calculate() -> None:
    engine = HealthScoreEngine()
    with patch.object(engine._doctor, "examine") as mock_examine:
        mock_examine.return_value = {
            "results": [
                {"name": "Infrastructure", "status": "PASS"},
                {"name": "Collection", "status": "PASS"},
                {"name": "Database", "status": "PASS"},
                {"name": "Pipelines", "status": "PASS"},
                {"name": "Finalizer", "status": "PASS"},
                {"name": "Registry", "status": "PASS"},
                {"name": "Discovery", "status": "PASS"},
                {"name": "Incidents", "status": "PASS"},
                {"name": "Notifications", "status": "WARNING"},
            ],
            "total_suites": 9,
            "passed": 8,
            "warnings": 1,
            "failed": 0,
        }
        score = engine.calculate()
        assert 90 <= score.score <= 100


def test_health_score_engine_with_failures() -> None:
    engine = HealthScoreEngine()
    with patch.object(engine._doctor, "examine") as mock_examine:
        mock_examine.return_value = {
            "results": [
                {"name": "Infrastructure", "status": "FAIL"},
                {"name": "Collection", "status": "FAIL"},
                {"name": "Database", "status": "FAIL"},
                {"name": "Pipelines", "status": "FAIL"},
                {"name": "Finalizer", "status": "PASS"},
                {"name": "Registry", "status": "PASS"},
                {"name": "Discovery", "status": "PASS"},
                {"name": "Incidents", "status": "PASS"},
                {"name": "Notifications", "status": "PASS"},
            ],
            "total_suites": 9,
            "passed": 5,
            "warnings": 0,
            "failed": 4,
        }
        score = engine.calculate()
        assert score.score < 50
