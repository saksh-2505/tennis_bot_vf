import io
import json
import logging
from unittest.mock import patch

import pytest

from observability.logging import JSONFormatter, TraceFilter, setup_structured_logging, get_logger
from observability.tracing import TraceContext


class TestStructuredLogging:
    def test_json_formatter_output(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger", level=logging.INFO, pathname="test.py",
            lineno=42, msg="hello world", args=(), exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "hello world"
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test_logger"
        assert "timestamp" in parsed
        assert "trace_id" in parsed

    def test_trace_filter_injects_ids(self):
        with TraceContext("test_op", "svc", "mod", "comp") as ctx:
            filt = TraceFilter()
            record = logging.LogRecord("x", logging.INFO, "x.py", 1, "msg", (), None)
            filt.filter(record)
            assert record.trace_id == ctx.trace_id
            assert record.span_id == ctx.span_id

    def test_setup_structured_logging(self):
        with patch("sys.stdout", io.StringIO()) as mock_stdout:
            setup_structured_logging(level="DEBUG", service_name="test_svc")
            logger = get_logger("test_logger")
            logger.info("test message")
            output = mock_stdout.getvalue()
            parsed = json.loads(output.strip())
            assert parsed["message"] == "test message"
            assert parsed["service"] == "test_svc"

    def test_structured_logger_extra_fields(self):
        with patch("sys.stdout", io.StringIO()) as mock_stdout:
            setup_structured_logging(level="DEBUG")
            logger = get_logger("test_logger")
            logger.info("with extra", tracked_match_id=42, operation="test_op")
            output = mock_stdout.getvalue()
            parsed = json.loads(output.strip())
            assert parsed["message"] == "with extra"
            assert parsed["metadata"]["tracked_match_id"] == 42
            assert parsed["metadata"]["operation"] == "test_op"

    def test_operation_log(self):
        with patch("sys.stdout", io.StringIO()) as mock_stdout:
            setup_structured_logging(level="DEBUG")
            logger = get_logger("op_logger")
            logger.operation("do_work", status="ok", duration_ms=15.0)
            output = mock_stdout.getvalue()
            parsed = json.loads(output.strip())
            assert parsed["metadata"]["operation"] == "do_work"
            assert parsed["metadata"]["status"] == "ok"
            assert parsed["metadata"]["duration_ms"] == 15.0

    def test_error_logging(self):
        with patch("sys.stdout", io.StringIO()) as mock_stdout:
            setup_structured_logging(level="DEBUG")
            logger = get_logger("err_logger")
            try:
                raise ValueError("boom")
            except ValueError:
                logger.exception("something failed")
            output = mock_stdout.getvalue()
            parsed = json.loads(output.strip())
            assert parsed["message"] == "something failed"
            assert parsed["exception"]["type"] == "ValueError"
