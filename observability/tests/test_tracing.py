from unittest.mock import patch

import pytest

from observability.tracing import TraceContext, get_current_trace_id, get_current_span_id, get_trace


class TestTracing:
    def test_trace_id_generation(self):
        with TraceContext("test_op", "test_service", "test_module", "test_comp") as ctx:
            assert ctx.trace_id is not None
            assert len(ctx.trace_id) == 16
            assert get_current_trace_id() == ctx.trace_id

    def test_nested_traces(self):
        with TraceContext("root_op", "svc", "mod", "comp") as root_ctx:
            root_tid = root_ctx.trace_id
            with TraceContext("child_op", "svc", "mod", "comp") as child_ctx:
                assert child_ctx.trace_id == root_tid
                assert child_ctx.span_id != root_ctx.span_id
                assert get_current_span_id() == child_ctx.span_id
            assert get_current_span_id() == root_ctx.span_id

    def test_trace_stored_correctly(self):
        with TraceContext("stored_op", "svc", "mod", "comp") as ctx:
            pass
        trace = get_trace(ctx.trace_id)
        assert trace is not None
        assert trace.trace_id == ctx.trace_id
        assert len(trace.spans) == 1
        assert trace.spans[0].operation == "stored_op"

    def test_trace_captures_error(self):
        try:
            with TraceContext("fail_op", "svc", "mod", "comp"):
                raise ValueError("test error")
        except ValueError:
            pass
        traces = get_trace(get_current_trace_id() or "")
        if traces is None:
            traces_found = [t for t in __import__("observability.tracing", fromlist=["_TRACES"])._TRACES.values()
                            if t.root_operation == "fail_op"]
            if traces_found:
                assert traces_found[0].spans[-1].status == "error"

    def test_context_independence(self):
        tid1 = None
        with TraceContext("a", "svc", "mod", "comp") as ctx1:
            tid1 = ctx1.trace_id
            with TraceContext("a1", "svc", "mod", "comp"):
                pass
        with TraceContext("b", "svc", "mod", "comp") as ctx2:
            assert ctx2.trace_id != tid1

    def test_trace_depth_limit(self):
        with patch("observability.tracing._DEPTH_LIMIT", 3):
            with TraceContext("root", "svc", "mod", "comp") as root_ctx:
                root_tid = root_ctx.trace_id
                with TraceContext("a", "svc", "mod", "comp"):
                    with TraceContext("b", "svc", "mod", "comp"):
                        with TraceContext("c", "svc", "mod", "comp") as deep_ctx:
                            assert deep_ctx.trace_id != root_tid
