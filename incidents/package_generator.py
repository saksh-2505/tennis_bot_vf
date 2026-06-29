"""Incident diagnostic package: logs, metrics, state, config."""
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import text

from database import engine
from incidents.config import INCIDENT_PACKAGES_DIR, SECRET_KEY_PATTERNS
from incidents.models import Incident

logger = logging.getLogger(__name__)


def generate_incident_package(session: Session, incident: Incident) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    package_dir = Path(INCIDENT_PACKAGES_DIR) / f"INC_{incident.incident_id}_{ts}"
    package_dir.mkdir(parents=True, exist_ok=True)

    _write_incident_json(package_dir, incident)
    _collect_logs(package_dir, incident)
    _collect_metrics(package_dir)
    _collect_environment(package_dir)
    _collect_system_state(package_dir, session)
    _collect_configuration(package_dir)
    _collect_architecture(package_dir)
    _collect_source(package_dir, incident)

    logger.info("Incident package generated: %s", package_dir)
    return str(package_dir)


def _write_incident_json(package_dir: Path, incident: Incident) -> None:
    data = {
        "incident_id": incident.incident_id,
        "severity": incident.severity,
        "category": incident.category,
        "module": incident.module,
        "title": incident.title,
        "summary": incident.summary,
        "status": incident.status,
        "tracked_match_id": incident.tracked_match_id,
        "collector_name": incident.collector_name,
        "first_detected_at": _iso(incident.first_detected_at),
        "last_detected_at": _iso(incident.last_detected_at),
        "resolved_at": _iso(incident.resolved_at) if incident.resolved_at else None,
        "occurrence_count": incident.occurrence_count,
        "recovery_attempts": incident.recovery_attempts,
    }
    (package_dir / "incident.json").write_text(json.dumps(data, indent=2, default=str))


def _collect_logs(package_dir: Path, incident: Incident) -> None:
    logs_dir = package_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    try:
        compose_dir = os.path.expanduser("~/tennis_bot")
        if not os.path.isdir(compose_dir):
            compose_dir = os.getcwd()

        result = subprocess.run(
            ["docker", "compose", "logs", "--tail", "500", "app"],
            capture_output=True, text=True, timeout=30, cwd=compose_dir,
        )
        if result.stdout.strip():
            (logs_dir / "app_recent.log").write_text(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        (logs_dir / "_collection_note.txt").write_text(
            f"Could not collect app logs: {e}\n"
            "Running inside container without Docker socket access.\n"
        )

    log_paths = _find_log_files(incident.module)
    for label, path in log_paths:
        try:
            content = Path(path).read_text()
            truncated = "\n".join(content.split("\n")[-500:])
            (logs_dir / f"{label}.log").write_text(truncated)
        except OSError:
            pass


def _find_log_files(module: str) -> list[tuple[str, str]]:
    candidates = []
    log_locations = [
        "/tmp/tennis_bot_monitor.log",
        "/tmp/tennis_bot_health.log",
    ]
    for loc in log_locations:
        if os.path.exists(loc):
            candidates.append((Path(loc).stem, loc))
    return candidates


def _collect_metrics(package_dir: Path) -> None:
    metrics = {}

    try:
        loadavg = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        metrics["cpu_percent"] = round((loadavg[0] / cpu_count) * 100, 1)
        metrics["cpu_load_1min"] = round(loadavg[0], 2)
        metrics["cpu_load_5min"] = round(loadavg[1], 2)
        metrics["cpu_load_15min"] = round(loadavg[2], 2)
        metrics["cpu_cores"] = cpu_count
    except (OSError, AttributeError):
        metrics["cpu"] = "unavailable"

    try:
        mem = _parse_meminfo()
        if mem.get("MemTotal") and mem.get("MemAvailable"):
            total = mem["MemTotal"]
            used = total - mem["MemAvailable"]
            metrics["memory_total_kb"] = total
            metrics["memory_used_kb"] = used
            metrics["memory_percent"] = round((used / total) * 100, 1)
    except (OSError, FileNotFoundError):
        metrics["memory"] = "unavailable"

    try:
        usage = shutil.disk_usage("/")
        metrics["disk_total_gb"] = round(usage.total / (1024 ** 3), 1)
        metrics["disk_used_gb"] = round(usage.used / (1024 ** 3), 1)
        metrics["disk_free_gb"] = round(usage.free / (1024 ** 3), 1)
        metrics["disk_percent"] = round((usage.used / usage.total) * 100, 1)
    except OSError:
        metrics["disk"] = "unavailable"

    (package_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))


def _collect_environment(package_dir: Path) -> None:
    env = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "os_name": platform.system(),
        "os_release": platform.release(),
        "hostname": platform.node(),
        "installed_packages": _pip_freeze(),
        "database_version": _db_version(),
    }

    try:
        result = subprocess.run(
            ["docker", "--version"], capture_output=True, text=True, timeout=5
        )
        env["docker_version"] = result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        env["docker_version"] = "unavailable"

    (package_dir / "environment.json").write_text(json.dumps(env, indent=2, default=str))


def _collect_system_state(package_dir: Path, session: Session) -> None:
    state = {}

    try:
        result = session.execute(
            text("SELECT status, count(*) FROM tracked_matches GROUP BY status")
        )
        state["active_matches"] = {row[0]: row[1] for row in result}
    except Exception as e:
        state["active_matches_error"] = str(e)

    try:
        result = session.execute(text("SELECT count(*) FROM live_scores"))
        state["score_tick_count"] = result.scalar()
    except Exception:
        state["score_tick_count"] = "unavailable"

    try:
        result = session.execute(text("SELECT count(*) FROM live_odds"))
        state["odds_tick_count"] = result.scalar()
    except Exception:
        state["odds_tick_count"] = "unavailable"

    try:
        result = session.execute(text("SELECT count(*) FROM completed_matches"))
        state["completed_matches"] = result.scalar()
    except Exception:
        state["completed_matches"] = "unavailable"

    try:
        result = session.execute(text(
            "SELECT count(*) FROM incidents WHERE status IN ('OPEN', 'ACKNOWLEDGED', 'RECOVERING')"
        ))
        state["open_incidents"] = result.scalar()
    except Exception:
        state["open_incidents"] = "unavailable"

    (package_dir / "state.json").write_text(json.dumps(state, indent=2, default=str))


def _collect_configuration(package_dir: Path) -> None:
    config = {}
    env_files = [
        os.path.expanduser("~/tennis_bot/.env"),
        os.path.join(os.getcwd(), ".env"),
    ]

    for env_path in env_files:
        if os.path.exists(env_path):
            for line in Path(env_path).read_text().split("\n"):
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                config[key] = _sanitize_value(key, value)
            break

    if not config:
        config["note"] = ".env file not found"

    (package_dir / "config.json").write_text(json.dumps(config, indent=2, default=str))


def _collect_architecture(package_dir: Path) -> None:
    arch = {}
    candidates = [
        os.path.join(os.getcwd(), "architecture.md"),
        os.path.expanduser("~/tennis_bot/architecture.md"),
    ]

    for path in candidates:
        if os.path.exists(path):
            arch["architecture_file"] = path
            break
    else:
        arch["architecture_file"] = "not found"

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=os.getcwd(),
        )
        arch["git_commit"] = result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        arch["git_commit"] = "unavailable"

    (package_dir / "architecture.json").write_text(json.dumps(arch, indent=2))


def _collect_source(package_dir: Path, incident: Incident) -> None:
    source_dir = package_dir / "source"
    source_dir.mkdir(exist_ok=True)

    module_name = incident.module
    source_files = _find_source_files(module_name)

    for src_path in source_files:
        if os.path.exists(src_path):
            dest = source_dir / os.path.basename(src_path)
            shutil.copy2(src_path, dest)

    if not any(source_dir.iterdir()):
        (source_dir / "_not_found.txt").write_text(
            f"Could not locate source files for module: {module_name}\n"
            f"Searched: {source_files}\n"
        )


def _find_source_files(module_name: str) -> list[str]:
    cwd = os.getcwd()
    candidates = []

    if "/" in module_name or "." in module_name:
        parts = module_name.replace(".", "/").split("/")
        path = os.path.join(cwd, *parts)
        candidates.append(f"{path}.py")
        if parts:
            candidates.append(os.path.join(cwd, *parts, "__init__.py"))
            candidates.append(os.path.join(cwd, *parts, "service.py"))
    else:
        candidates.append(os.path.join(cwd, module_name, "__init__.py"))
        candidates.append(os.path.join(cwd, module_name, "service.py"))
        candidates.append(os.path.join(cwd, f"{module_name}.py"))

    return [c for c in candidates if os.path.exists(c)] or candidates


def _sanitize_value(key: str, value: str) -> str:
    key_lower = key.lower()
    for pattern in SECRET_KEY_PATTERNS:
        if pattern in key_lower:
            return "<REDACTED>"
    return value


def _parse_meminfo() -> dict[str, int]:
    mem = {}
    with open("/proc/meminfo") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2:
                key = parts[0].rstrip(":")
                try:
                    mem[key] = int(parts[1])
                except ValueError:
                    pass
    return mem


def _pip_freeze() -> list[str]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True, text=True, timeout=15,
        )
        return [pkg.strip() for pkg in result.stdout.strip().split("\n") if pkg.strip()]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ["pip_freeze_unavailable"]


def _db_version() -> str:
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            return result.scalar_one()
    except Exception:
        return "unavailable"


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()
