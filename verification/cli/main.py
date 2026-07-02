"""Verification CLI.

Usage:
    python -m verification.cli verify
    python -m verification.cli doctor
    python -m verification.cli report
    python -m verification.cli health
    python -m verification.cli verify collection
    python -m verification.cli verify database
    python -m verification.cli verify pipeline
    python -m verification.cli verify dataset
"""
from __future__ import annotations

import sys
from typing import NoReturn


def _print_usage() -> None:
    print("Usage: python -m verification.cli <command> [<subcommand>]")
    print()
    print("Commands:")
    print("  platform verify              Run all verification suites")
    print("  platform verify <suite>      Verify specific suite (infrastructure, collection, database, pipeline, dataset, registry, finalizer, discovery, incidents, notifications)")
    print("  platform doctor              Run Platform Doctor")
    print("  platform report              Generate daily report")
    print("  platform health              Show latest health score")


VALID_SUITES = {
    "infrastructure", "collection", "database", "pipeline", "dataset",
    "registry", "finalizer", "discovery", "incidents", "notifications",
}

_SUITE_MAP = {
    "infrastructure": "verify_infrastructure",
    "discovery": "verify_discovery",
    "registry": "verify_registry",
    "collection": "verify_collection",
    "database": "verify_database",
    "finalizer": "verify_finalizer",
    "dataset": "verify_dataset",
    "incidents": "verify_incidents",
    "notifications": "verify_notifications",
    "pipeline": "verify_pipeline",
}


def main(argv: list[str] | None = None) -> None:
    args = argv or sys.argv[1:]
    if not args:
        _print_usage()
        return

    cmd = args[0]

    if cmd == "verify":
        _handle_verify(args[1:])
    elif cmd == "doctor":
        _handle_doctor()
    elif cmd == "report":
        _handle_report()
    elif cmd == "health":
        _handle_health()
    else:
        print(f"Unknown command: {cmd}")
        _print_usage()
        sys.exit(1)


def _handle_verify(args: list[str]) -> None:
    if not args:
        _run_all_verifications()
        return

    suite = args[0].lower()
    if suite not in VALID_SUITES:
        print(f"Unknown suite: {suite}")
        print(f"Available: {', '.join(sorted(VALID_SUITES))}")
        sys.exit(1)

    func_name = _SUITE_MAP[suite]
    mod = __import__("verification.api", fromlist=[func_name])
    func = getattr(mod, func_name)
    report = func()
    _print_report(report)


def _run_all_verifications() -> None:
    from verification.api import verify_platform
    reports = verify_platform()
    for report in reports:
        _print_report(report)
        print()


def _handle_doctor() -> None:
    from verification.doctor import PlatformDoctor
    doctor = PlatformDoctor()
    print(doctor.print_report())


def _handle_report() -> None:
    from verification.reports.generator import generate_daily_report, save_daily_report
    report = generate_daily_report()
    filepath = save_daily_report(report)
    print(f"Daily report generated and saved to {filepath}")
    print(f"Health Score: {report.platform_health_score}/100")
    print(f"Infrastructure: {report.infrastructure_status}")
    print(f"Collection:     {report.collection_health}")
    print(f"Database:       {report.database_health}")
    print(f"Pipeline:       {report.pipeline_health}")
    print(f"Completed:      {report.completed_matches}")
    if report.incident_summary:
        print(f"Incidents:      {report.incident_summary}")
    if report.historical_trend:
        print(f"Trend:          {report.historical_trend}")


def _handle_health() -> None:
    from verification.health_score import HealthScoreEngine
    engine = HealthScoreEngine()
    score = engine.calculate()
    print(f"Platform Health Score: {score.score}/100")
    print()
    for factor, val in sorted(score.factors.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(val * 20 / 100) if 100 else ""
        print(f"  {factor:<18} {val:5.1f}  {bar}")


def _print_report(report) -> None:
    icon = {"PASS": "✓", "WARNING": "⚠", "FAIL": "✗"}.get(report.status, "?")
    print(f"[{icon}] {report.verification_type.upper():<20} {report.status:<10} "
          f"({report.duration:.3f}s)")
    print(f"  {report.summary}")
    if report.failures:
        for f in report.failures[:5]:
            print(f"  FAIL: {f}")
    if report.warnings:
        for w in report.warnings[:5]:
            print(f"  WARN: {w}")
    if report.recommendations:
        for r in report.recommendations[:3]:
            print(f"  REC:  {r}")
    if report.metrics:
        key_metrics = {k: v for k, v in sorted(report.metrics.items())[:8]}
        print(f"  Metrics: {key_metrics}")


if __name__ == "__main__":
    main()
