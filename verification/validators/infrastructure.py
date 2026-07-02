"""Infrastructure Verification.

Verify: Oracle VM reachable, Docker healthy, PostgreSQL connected,
TimescaleDB healthy, disk/memory/CPU, internet, DNS, time sync.
"""
from __future__ import annotations

import os
import socket
import subprocess
import time
from datetime import datetime, timezone

from database import SessionLocal
from sqlalchemy import text

from verification.framework.base import BaseVerifier
from verification.framework.evidence import query_evidence
from verification.models import VerificationReport


class InfrastructureVerifier(BaseVerifier):
    verification_type: str = "infrastructure"

    def verify(self) -> VerificationReport:
        failures: list[str] = []
        warnings: list[str] = []
        metrics: dict = {}

        self._check_oracle_vm(failures)
        self._check_docker(failures, warnings, metrics)
        self._check_postgresql(failures, metrics)
        self._check_timescaledb(failures, metrics)
        self._check_disk(failures, warnings, metrics)
        self._check_memory(failures, warnings, metrics)
        self._check_cpu(failures, warnings, metrics)
        self._check_internet(failures)
        self._check_dns(failures)
        self._check_time_sync(failures, warnings)

        status = "PASS"
        summary = "All infrastructure checks passed."

        if warnings and not failures:
            status = "WARNING"
            summary = f"{len(warnings)} warning(s) detected."
        if failures:
            status = "FAIL"
            summary = f"{len(failures)} failure(s) detected."

        return self._build_report(
            status=status,
            summary=summary,
            failures=failures,
            warnings=warnings,
            metrics=metrics,
        )

    def _check_oracle_vm(self, failures: list[str]) -> None:
        hostname = socket.gethostname()
        self.add_evidence("vm_hostname", hostname)
        # no specific check — just record hostname

    def _check_docker(self, failures: list[str], warnings: list[str], metrics: dict) -> None:
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                failures.append(f"Docker: command failed ({result.stderr.strip()})")
                return
            lines = [l for l in result.stdout.strip().split("\n") if l]
            self.add_evidence("docker_containers", len(lines), f"{len(lines)} running containers")
            metrics["docker_containers"] = len(lines)
            unhealthy = [l for l in lines if "(healthy)" not in l.lower() and "(unhealthy)" in l.lower()]
            if unhealthy:
                for u in unhealthy:
                    failures.append(f"Docker unhealthy container: {u.split(chr(9))[0]}")
        except FileNotFoundError:
            warnings.append("Docker: command not found (not running on host)")
        except Exception as e:
            warnings.append(f"Docker: check failed ({e})")

    def _check_postgresql(self, failures: list[str], metrics: dict) -> None:
        try:
            with SessionLocal() as session:
                start = time.time()
                result = session.execute(text("SELECT 1"))
                latency = round((time.time() - start) * 1000, 1)
                self.add_evidence("postgresql_latency_ms", latency)
                metrics["postgresql_latency_ms"] = latency
                if latency > 500:
                    failures.append(f"PostgreSQL: high latency ({latency}ms)")
        except Exception as e:
            failures.append(f"PostgreSQL: connection failed ({e})")

    def _check_timescaledb(self, failures: list[str], metrics: dict) -> None:
        try:
            with SessionLocal() as session:
                result = session.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'"))
                row = result.fetchone()
                if row:
                    version = row[0]
                    self.add_evidence("timescaledb_version", version)
                    metrics["timescaledb_version"] = version
                    # check hypertable health
                    result2 = session.execute(text(
                        "SELECT hypertable_schema, hypertable_name, num_chunks, compression_enabled "
                        "FROM timescaledb_information.hypertables"
                    ))
                    hypertables = [dict(row._mapping) for row in result2]
                    self.add_evidence("hypertables", hypertables)
                    metrics["hypertable_count"] = len(hypertables)
                    for ht in hypertables:
                        if ht.get("num_chunks") == 0:
                            failures.append(f"TimescaleDB: hypertable {ht['hypertable_name']} has 0 chunks")
                else:
                    failures.append("TimescaleDB: extension not installed")
        except Exception as e:
            failures.append(f"TimescaleDB: health check failed ({e})")

    def _check_disk(self, failures: list[str], warnings: list[str], metrics: dict) -> None:
        try:
            stat = os.statvfs("/")
            total = stat.f_frsize * stat.f_blocks
            free = stat.f_frsize * stat.f_bavail
            used_pct = round((1 - free / total) * 100, 1) if total else 0
            self.add_evidence("disk_used_pct", used_pct)
            metrics["disk_used_percent"] = used_pct
            if used_pct > 95:
                failures.append(f"Disk: {used_pct}% used (critical)")
            elif used_pct > 85:
                warnings.append(f"Disk: {used_pct}% used (warning)")
        except Exception as e:
            warnings.append(f"Disk: check failed ({e})")

    def _check_memory(self, failures: list[str], warnings: list[str], metrics: dict) -> None:
        try:
            with open("/proc/meminfo") as f:
                lines = f.readlines()
            mem = {}
            for line in lines:
                parts = line.split(":")
                if len(parts) >= 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    mem[key] = int(val)
            total = mem.get("MemTotal", 0)
            available = mem.get("MemAvailable", 0)
            used_pct = round((1 - available / total) * 100, 1) if total else 0
            self.add_evidence("memory_used_pct", used_pct)
            metrics["memory_used_percent"] = used_pct
            if used_pct > 95:
                failures.append(f"Memory: {used_pct}% used (critical)")
            elif used_pct > 85:
                warnings.append(f"Memory: {used_pct}% used (warning)")
        except Exception as e:
            warnings.append(f"Memory: check failed ({e})")

    def _check_cpu(self, failures: list[str], warnings: list[str], metrics: dict) -> None:
        try:
            load = os.getloadavg()
            self.add_evidence("load_avg", list(load))
            metrics["load_avg_1m"] = round(load[0], 2)
            metrics["load_avg_5m"] = round(load[1], 2)
            metrics["load_avg_15m"] = round(load[2], 2)
            cpu_count = os.cpu_count() or 1
            if load[0] > cpu_count * 2:
                failures.append(f"CPU: load {load[0]:.1f} > {cpu_count * 2} (critical)")
            elif load[0] > cpu_count:
                warnings.append(f"CPU: load {load[0]:.1f} > {cpu_count} (warning)")
        except Exception as e:
            warnings.append(f"CPU: check failed ({e})")

    def _check_internet(self, failures: list[str]) -> None:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(("8.8.8.8", 53))
            sock.close()
            self.add_evidence("internet", "reachable")
        except Exception:
            failures.append("Internet: cannot reach 8.8.8.8")

    def _check_dns(self, failures: list[str]) -> None:
        try:
            socket.getaddrinfo("google.com", 80)
            self.add_evidence("dns", "resolving")
        except Exception:
            failures.append("DNS: cannot resolve google.com")

    def _check_time_sync(self, failures: list[str], warnings: list[str]) -> None:
        now_ts = datetime.now(timezone.utc).timestamp()
        self.add_evidence("system_time", datetime.now(timezone.utc).isoformat())
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect(("time.google.com", 123))
            sock.close()
        except Exception:
            warnings.append("Time sync: cannot reach NTP server")
