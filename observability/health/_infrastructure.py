from __future__ import annotations

import os
import shlex
import subprocess
import time
from datetime import datetime, timezone

from observability.health import make_health_report, register_health_check
from observability.models import HealthStatus
from observability.utils import get_cpu_usage, get_memory_usage, get_disk_usage


def _check_oracle_vm() -> HealthReport:
    try:
        result = subprocess.run(
            shlex.split("uptime"),
            capture_output=True, text=True, timeout=5,
        )
        uptime_str = result.stdout.strip()
        connected = result.returncode == 0
    except Exception:
        connected = False
        uptime_str = ""

    return make_health_report(
        service_name="Oracle VM",
        status=HealthStatus.HEALTHY if connected else HealthStatus.UNHEALTHY,
        uptime=time.time(),
        last_success=datetime.now(timezone.utc) if connected else None,
        last_error=None if connected else datetime.now(timezone.utc),
        details={"uptime_output": uptime_str} if uptime_str else None,
    )


def _check_docker() -> HealthReport:
    try:
        result = subprocess.run(
            shlex.split("docker info --format '{{.ServerVersion}}'"),
            capture_output=True, text=True, timeout=5,
        )
        version = result.stdout.strip()
        running = result.returncode == 0 and bool(version)
    except Exception:
        running = False
        version = ""

    return make_health_report(
        service_name="Docker",
        status=HealthStatus.HEALTHY if running else HealthStatus.UNHEALTHY,
        uptime=time.time(),
        last_success=datetime.now(timezone.utc) if running else None,
        last_error=None if running else datetime.now(timezone.utc),
        details={"version": version} if version else None,
    )


def _check_postgresql() -> HealthReport:
    try:
        from database import check_connection
        connected = check_connection()
    except Exception:
        connected = False

    return make_health_report(
        service_name="PostgreSQL",
        status=HealthStatus.HEALTHY if connected else HealthStatus.UNHEALTHY,
        uptime=time.time(),
        last_success=datetime.now(timezone.utc) if connected else None,
        last_error=None if connected else datetime.now(timezone.utc),
        details={"connection_ok": connected} if connected else None,
    )


def _check_timescaledb() -> HealthReport:
    try:
        from database import SessionLocal
        from sqlalchemy import text
        session = SessionLocal()
        try:
            result = session.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'"))
            row = result.fetchone()
            version = row[0] if row else None
            timescale_ok = version is not None
        finally:
            session.close()
    except Exception:
        timescale_ok = False
        version = None

    return make_health_report(
        service_name="TimescaleDB",
        status=HealthStatus.HEALTHY if timescale_ok else HealthStatus.DEGRADED,
        uptime=time.time(),
        last_success=datetime.now(timezone.utc) if timescale_ok else None,
        last_error=None if timescale_ok else datetime.now(timezone.utc),
        details={"version": version} if version else {"error": "timescaledb extension not found"},
    )


def register_infrastructure_health_checks() -> None:
    register_health_check("Oracle VM", _check_oracle_vm)
    register_health_check("Docker", _check_docker)
    register_health_check("PostgreSQL", _check_postgresql)
    register_health_check("TimescaleDB", _check_timescaledb)
