from __future__ import annotations

import dataclasses
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceState(str, Enum):
    RUNNING = "running"
    IDLE = "idle"
    STOPPED = "stopped"
    CRASHED = "crashed"
    RESTARTING = "restarting"


class PipelineStageStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"
    PENDING = "pending"


class TraceLevel(str, Enum):
    ROOT = "root"
    CHILD = "child"


@dataclasses.dataclass
class HealthReport:
    service_name: str
    status: HealthStatus
    uptime: float
    last_success: datetime | None
    last_error: datetime | None
    heartbeat_time: datetime | None
    active_tasks: int
    processed_items: int
    average_latency_ms: float
    cpu_usage: float
    memory_usage: float
    details: dict[str, Any] | None = None


@dataclasses.dataclass
class Span:
    span_id: str
    parent_span_id: str | None
    operation: str
    service: str
    module: str
    component: str
    started_at: datetime
    ended_at: datetime | None = None
    status: str = "running"
    metadata: dict[str, Any] | None = None


@dataclasses.dataclass
class Trace:
    trace_id: str
    spans: list[Span]
    started_at: datetime
    ended_at: datetime | None = None
    root_operation: str | None = None


@dataclasses.dataclass
class StructuredLogEntry:
    timestamp: str
    trace_id: str | None
    span_id: str | None
    service: str
    module: str
    component: str
    operation: str
    level: str
    status: str
    tracked_match_id: int | None
    incident_id: int | None
    duration_ms: float | None
    message: str
    metadata: dict[str, Any] | None


@dataclasses.dataclass
class MetricPoint:
    name: str
    value: float
    timestamp: datetime
    labels: dict[str, str] | None = None


@dataclasses.dataclass
class Counter:
    name: str
    _value: float = 0.0
    _lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)

    def inc(self, amount: float = 1.0) -> None:
        with self._lock:
            self._value += amount

    def get(self) -> float:
        with self._lock:
            return self._value

    def reset(self) -> None:
        with self._lock:
            self._value = 0.0


@dataclasses.dataclass
class Gauge:
    name: str
    _value: float = 0.0
    _lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)

    def set(self, value: float) -> None:
        with self._lock:
            self._value = value

    def get(self) -> float:
        with self._lock:
            return self._value


@dataclasses.dataclass
class Histogram:
    name: str
    _values: list[float] = dataclasses.field(default_factory=list)
    _lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)
    _max_samples: int = 1000

    def observe(self, value: float) -> None:
        with self._lock:
            self._values.append(value)
            if len(self._values) > self._max_samples:
                self._values = self._values[-self._max_samples:]

    def snapshot(self) -> dict[str, float]:
        with self._lock:
            if not self._values:
                return {"count": 0, "min": 0.0, "max": 0.0, "avg": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0}
            sorted_v = sorted(self._values)
            n = len(sorted_v)
            return {
                "count": n,
                "min": sorted_v[0],
                "max": sorted_v[-1],
                "avg": sum(sorted_v) / n,
                "p50": sorted_v[int(n * 0.5)],
                "p95": sorted_v[int(n * 0.95)],
                "p99": sorted_v[int(n * 0.99)],
            }


@dataclasses.dataclass
class PipelineStageResult:
    stage_name: str
    status: PipelineStageStatus
    duration_ms: float
    error: str | None = None
    details: dict[str, Any] | None = None


@dataclasses.dataclass
class PipelineResult:
    pipeline_name: str
    stages: list[PipelineStageResult]
    overall_status: PipelineStageStatus
    started_at: datetime
    ended_at: datetime
    first_failure: str | None = None


@dataclasses.dataclass
class MatchHealth:
    tracked_match_id: int
    status: str
    score_heartbeat: datetime | None = None
    odds_heartbeat: datetime | None = None
    last_score_timestamp: datetime | None = None
    last_odds_timestamp: datetime | None = None
    score_tick_rate: float = 0.0
    odds_tick_rate: float = 0.0
    collection_latency_ms: float = 0.0
    match_duration_seconds: float = 0.0
    validation_state: str | None = None
    diagnostics: list[str] | None = None


@dataclasses.dataclass
class ServiceHeartbeat:
    service_name: str
    state: ServiceState
    current_task: str | None = None
    active_threads: int = 0
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    response_time_ms: float = 0.0
    error_count: int = 0
    timestamp: datetime = dataclasses.field(default_factory=lambda: datetime.now(timezone.utc))


@dataclasses.dataclass
class TelegramDiagnostic:
    stage: str
    status: PipelineStageStatus
    duration_ms: float
    chat_id: str | None = None
    message_text_preview: str | None = None
    http_status_code: int | None = None
    telegram_message_id: int | None = None
    error: str | None = None
    timestamp: datetime = dataclasses.field(default_factory=lambda: datetime.now(timezone.utc))
