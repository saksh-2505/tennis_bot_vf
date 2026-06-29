from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any

from observability import config as obs_config
from observability.tracing import get_current_trace_id, get_current_span_id

_LOG_RECORD_ATTRS = frozenset(
    {
        "args", "asctime", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelno", "levelname", "lineno", "message",
        "module", "msecs", "msg", "name", "pathname", "process",
        "processName", "relativeCreated", "stack_info", "thread", "threadName",
    }
)

_OBSERVABILITY_SERVICE_NAME: str = "unknown"
_OBSERVABILITY_MODULE: str = "unknown"
_OBSERVABILITY_COMPONENT: str = "unknown"


def configure_observability_context(
    service_name: str = "unknown",
    module: str = "unknown",
    component: str = "unknown",
) -> None:
    global _OBSERVABILITY_SERVICE_NAME, _OBSERVABILITY_MODULE, _OBSERVABILITY_COMPONENT
    _OBSERVABILITY_SERVICE_NAME = service_name
    _OBSERVABILITY_MODULE = module
    _OBSERVABILITY_COMPONENT = component


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "trace_id": get_current_trace_id(),
            "span_id": get_current_span_id(),
            "service": _OBSERVABILITY_SERVICE_NAME,
            "component": _OBSERVABILITY_COMPONENT,
        }

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }

        extra_keys = set(record.__dict__.keys()) - _LOG_RECORD_ATTRS - {"trace_id", "span_id"}
        if extra_keys:
            log_entry["metadata"] = {k: record.__dict__[k] for k in extra_keys}

        return json.dumps(log_entry, default=str)


class TraceFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_current_trace_id()
        record.span_id = get_current_span_id()
        return True


def setup_structured_logging(
    level: str | None = None,
    service_name: str = "unknown",
    module: str = "unknown",
    component: str = "unknown",
) -> None:
    configure_observability_context(service_name, module, component)

    log_level = (level or obs_config.OBSERVABILITY_LOG_LEVEL).upper()
    fmt = obs_config.OBSERVABILITY_LOG_FORMAT

    if fmt == "json":
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        handler.addFilter(TraceFilter())

        root = logging.getLogger()
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(getattr(logging, log_level, logging.INFO))
    else:
        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
            stream=sys.stdout,
        )


class StructuredLogger:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def info(self, message: str, **extra: Any) -> None:
        self._logger.info(message, extra=extra)

    def warning(self, message: str, **extra: Any) -> None:
        self._logger.warning(message, extra=extra)

    def error(self, message: str, **extra: Any) -> None:
        self._logger.error(message, extra=extra)

    def debug(self, message: str, **extra: Any) -> None:
        self._logger.debug(message, extra=extra)

    def critical(self, message: str, **extra: Any) -> None:
        self._logger.critical(message, extra=extra)

    def exception(self, message: str, **extra: Any) -> None:
        self._logger.exception(message, extra=extra)

    def operation(
        self,
        operation: str,
        status: str = "ok",
        tracked_match_id: int | None = None,
        incident_id: int | None = None,
        duration_ms: float | None = None,
        **extra: Any,
    ) -> None:
        merged = {
            "operation": operation,
            "status": status,
            "tracked_match_id": tracked_match_id,
            "incident_id": incident_id,
            "duration_ms": duration_ms,
        }
        merged.update(extra)
        self._logger.info(f"[{operation}] {status}", extra=merged)


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(logging.getLogger(name))
