from unittest.mock import MagicMock

import pytest

from observability.models import PipelineStageStatus, TelegramDiagnostic
from observability.telegram_diagnostics import (
    record_telegram_stage,
    get_telegram_diagnostics,
    validate_telegram_pipeline,
)


class TestTelegramDiagnostics:
    def setup_method(self):
        from observability import telegram_diagnostics
        telegram_diagnostics._telegram_diagnostics.clear()

    def test_record_and_get(self):
        record_telegram_stage("test_stage", PipelineStageStatus.PASS, 5.0, chat_id="123")
        diags = get_telegram_diagnostics()
        assert len(diags) == 1
        assert diags[0].stage == "test_stage"
        assert diags[0].status == PipelineStageStatus.PASS
        assert diags[0].duration_ms == 5.0
        assert diags[0].chat_id == "123"

    def test_record_failure(self):
        record_telegram_stage("http_request", PipelineStageStatus.FAIL, 100.0,
                              error="HTTP 429", http_status_code=429)
        diags = get_telegram_diagnostics()
        assert diags[0].status == PipelineStageStatus.FAIL
        assert diags[0].error == "HTTP 429"
        assert diags[0].http_status_code == 429

    def test_get_empty(self):
        assert len(get_telegram_diagnostics()) == 0

    def test_max_diagnostics(self):
        from observability import telegram_diagnostics
        for i in range(1100):
            record_telegram_stage(f"stage_{i}", PipelineStageStatus.PASS, float(i))
        diags = get_telegram_diagnostics(2000)
        assert len(diags) <= 1000

    def test_limit(self):
        for i in range(10):
            record_telegram_stage(f"s{i}", PipelineStageStatus.PASS, float(i))
        diags = get_telegram_diagnostics(limit=3)
        assert len(diags) == 3

    def test_validate_pipeline_success(self):
        def mock_send(text):
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"result": {"message_id": 42}}
            return resp
        result = validate_telegram_pipeline("hello", "chat_1", mock_send)
        assert result.stage == "complete"
        assert result.status == PipelineStageStatus.PASS

    def test_validate_pipeline_http_failure(self):
        def mock_send(text):
            resp = MagicMock()
            resp.status_code = 429
            return resp
        result = validate_telegram_pipeline("hello", "chat_1", mock_send)
        assert result.status == PipelineStageStatus.FAIL
        assert "429" in (result.error or "")

    def test_validate_pipeline_exception(self):
        def mock_send(text):
            raise ConnectionError("connection refused")
        result = validate_telegram_pipeline("hello", "chat_1", mock_send)
        assert result.status == PipelineStageStatus.FAIL
        assert "connection refused" in (result.error or "")
