"""Tests for verification framework base classes."""
from __future__ import annotations

from verification.framework.base import BaseVerifier
from verification.models import Evidence, VerificationReport


def test_base_verifier_run_calls_verify() -> None:
    class TestVerifier(BaseVerifier):
        verification_type = "test"

        def verify(self) -> VerificationReport:
            return self._build_report("PASS", "All good")

    verifier = TestVerifier()
    report = verifier.run()

    assert report.status == "PASS"
    assert report.summary == "All good"
    assert report.verification_type == "test"
    assert report.duration >= 0


def test_base_verifier_add_evidence() -> None:
    class TestVerifier(BaseVerifier):
        verification_type = "test"

        def verify(self) -> VerificationReport:
            self.add_evidence("key1", 42, "the answer")
            return self._build_report("PASS", "ok")

    verifier = TestVerifier()
    report = verifier.run()

    assert len(report.evidence) == 1
    assert report.evidence[0].key == "key1"
    assert report.evidence[0].value == 42
    assert report.evidence[0].description == "the answer"


def test_base_verifier_handles_exception() -> None:
    class FailingVerifier(BaseVerifier):
        verification_type = "failing"

        def verify(self) -> VerificationReport:
            raise RuntimeError("something broke")

    verifier = FailingVerifier()
    report = verifier.run()

    assert report.status == "FAIL"
    assert "something broke" in report.summary
    assert len(report.failures) == 1


def test_base_verifier_report_to_dict() -> None:
    class TestVerifier(BaseVerifier):
        verification_type = "test"

        def verify(self) -> VerificationReport:
            return self._build_report(
                "PASS", "ok", metrics={"count": 10}, failures=[], warnings=[]
            )

    verifier = TestVerifier()
    report = verifier.run()
    d = report.to_dict()

    assert d["status"] == "PASS"
    assert d["verification_type"] == "test"
    assert d["metrics"]["count"] == 10


def test_verification_report_is_healthy() -> None:
    report = VerificationReport(
        verification_id="abc",
        verification_type="test",
        started_at=None,  # type: ignore
        completed_at=None,  # type: ignore
        duration=0.0,
        status="PASS",
        summary="ok",
    )
    assert report.is_healthy()

    report.status = "FAIL"
    assert not report.is_healthy()


def test_health_score_to_dict() -> None:
    from verification.models import HealthScore
    hs = HealthScore(score=85, factors={"infra": 15.0, "db": 12.0})
    d = hs.to_dict()
    assert d["score"] == 85
    assert d["factors"]["infra"] == 15.0
