from __future__ import annotations

import contextvars
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from observability import config
from observability.models import Span, Trace

_current_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("_current_trace_id", default=None)
_current_span_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("_current_span_id", default=None)
_current_span_stack: contextvars.ContextVar[list[str]] = contextvars.ContextVar("_current_span_stack", default=[])

_TRACES: dict[str, Trace] = {}
_DEPTH_LIMIT = config.OBSERVABILITY_TRACE_MAX_DEPTH


def new_trace_id() -> str:
    return uuid.uuid4().hex[:16]


def new_span_id() -> str:
    return uuid.uuid4().hex[:12]


def get_current_trace_id() -> str | None:
    return _current_trace_id.get()


def get_current_span_id() -> str | None:
    return _current_span_id.get()


def get_current_stack_depth() -> int:
    return len(_current_span_stack.get())


def get_trace(trace_id: str) -> Trace | None:
    return _TRACES.get(trace_id)


def get_all_traces() -> list[Trace]:
    return list(_TRACES.values())


def clear_traces() -> None:
    _TRACES.clear()


class TraceContext:
    def __init__(
        self,
        operation: str,
        service: str = "unknown",
        module: str = "unknown",
        component: str = "unknown",
        metadata: dict[str, Any] | None = None,
    ):
        self._operation = operation
        self._service = service
        self._module = module
        self._component = component
        self._metadata = metadata or {}
        self._trace_id: str | None = None
        self._span_id: str | None = None
        self._parent_span_id: str | None = None
        self._started_at: datetime | None = None
        self._is_root: bool = False

    def __enter__(self) -> TraceContext:
        self._started_at = datetime.now(timezone.utc)
        parent_trace_id = _current_trace_id.get()
        parent_span_id = _current_span_id.get()
        stack = _current_span_stack.get()

        if parent_trace_id is None or get_current_stack_depth() >= _DEPTH_LIMIT:
            self._trace_id = new_trace_id()
            self._span_id = new_span_id()
            self._parent_span_id = None
            self._is_root = True
        else:
            self._trace_id = parent_trace_id
            self._span_id = new_span_id()
            self._parent_span_id = parent_span_id
            self._is_root = False

        new_stack = list(stack)
        new_stack.append(self._span_id)
        _current_trace_id.set(self._trace_id)
        _current_span_id.set(self._span_id)
        _current_span_stack.set(new_stack)

        span = Span(
            span_id=self._span_id,
            parent_span_id=self._parent_span_id,
            operation=self._operation,
            service=self._service,
            module=self._module,
            component=self._component,
            started_at=self._started_at,
            metadata=self._metadata,
        )

        if self._trace_id not in _TRACES:
            stored = _TRACES.get(self._trace_id)
            if stored is None:
                _TRACES[self._trace_id] = Trace(
                    trace_id=self._trace_id,
                    spans=[span],
                    started_at=self._started_at,
                    root_operation=self._operation if self._is_root else None,
                )
            else:
                stored.spans.append(span)
        else:
            _TRACES[self._trace_id].spans.append(span)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        ended_at = datetime.now(timezone.utc)
        trace = _TRACES.get(self._trace_id or "")
        if trace:
            for s in trace.spans:
                if s.span_id == self._span_id:
                    s.ended_at = ended_at
                    s.status = "error" if exc_type else "ok"
                    break
            if self._is_root:
                trace.ended_at = ended_at

        stack = _current_span_stack.get()
        if self._span_id in stack:
            new_stack = [s for s in stack if s != self._span_id]
            _current_span_stack.set(new_stack)
        else:
            new_stack = list(stack)

        if new_stack:
            _current_span_id.set(new_stack[-1])
        else:
            _current_span_id.set(None)
        if self._is_root:
            _current_trace_id.set(None)
            _current_span_id.set(None)

    @property
    def trace_id(self) -> str | None:
        return self._trace_id

    @property
    def span_id(self) -> str | None:
        return self._span_id

    def set_metadata(self, key: str, value: Any) -> None:
        trace = _TRACES.get(self._trace_id or "")
        if trace:
            for s in trace.spans:
                if s.span_id == self._span_id:
                    if s.metadata is None:
                        s.metadata = {}
                    s.metadata[key] = value
                    break
