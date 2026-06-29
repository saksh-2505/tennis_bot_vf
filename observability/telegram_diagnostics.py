from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from observability import config as obs_config
from observability.models import PipelineStageStatus, TelegramDiagnostic

_telegram_diagnostics: list[TelegramDiagnostic] = []
_MAX_DIAGNOSTICS = 1000


def record_telegram_stage(
    stage: str,
    status: PipelineStageStatus,
    duration_ms: float,
    chat_id: str | None = None,
    message_text_preview: str | None = None,
    http_status_code: int | None = None,
    telegram_message_id: int | None = None,
    error: str | None = None,
) -> None:
    diag = TelegramDiagnostic(
        stage=stage,
        status=status,
        duration_ms=duration_ms,
        chat_id=chat_id,
        message_text_preview=message_text_preview[:100] if message_text_preview else None,
        http_status_code=http_status_code,
        telegram_message_id=telegram_message_id,
        error=error,
    )
    _telegram_diagnostics.append(diag)
    if len(_telegram_diagnostics) > _MAX_DIAGNOSTICS:
        _telegram_diagnostics[:] = _telegram_diagnostics[-_MAX_DIAGNOSTICS:]


def get_telegram_diagnostics(limit: int = 50) -> list[TelegramDiagnostic]:
    return list(_telegram_diagnostics[-limit:])


def validate_telegram_pipeline(
    message_text: str,
    chat_id: str,
    send_fn: Any,
    timeout: float | None = None,
) -> TelegramDiagnostic:
    timeout = timeout or obs_config.OBSERVABILITY_TELEGRAM_TIMEOUT_SECONDS

    t0 = time.monotonic()
    record_telegram_stage("Message Created", PipelineStageStatus.PASS, 0.0, chat_id, message_text)

    t1 = time.monotonic()
    record_telegram_stage("Formatting", PipelineStageStatus.PASS, (t1 - t0) * 1000.0, chat_id)

    t2 = time.monotonic()
    record_telegram_stage("Escaping", PipelineStageStatus.PASS, (t2 - t1) * 1000.0, chat_id)

    t3 = time.monotonic()
    try:
        result = send_fn(message_text)
        t4 = time.monotonic()
        http_status = getattr(result, "status_code", None) if hasattr(result, "status_code") else None
        msg_id = None
        if isinstance(result, dict):
            http_status = result.get("status_code")
            msg_id = result.get("message_id")
        elif hasattr(result, "json"):
            try:
                resp_json = result.json()
                msg_id = resp_json.get("result", {}).get("message_id") if isinstance(resp_json, dict) else None
            except Exception:
                pass
        success = http_status == 200 or bool(msg_id) if http_status else True
        record_telegram_stage(
            "HTTP Request",
            PipelineStageStatus.PASS if success else PipelineStageStatus.FAIL,
            (t4 - t3) * 1000.0,
            chat_id,
            http_status_code=http_status,
            error=None if success else f"HTTP {http_status}",
        )
        if success:
            t5 = time.monotonic()
            record_telegram_stage("Telegram Response", PipelineStageStatus.PASS, (t5 - t4) * 1000.0, chat_id,
                                  telegram_message_id=msg_id)
            t6 = time.monotonic()
            record_telegram_stage("Logged", PipelineStageStatus.PASS, (t6 - t5) * 1000.0, chat_id,
                                  telegram_message_id=msg_id)
            return TelegramDiagnostic(
                stage="complete", status=PipelineStageStatus.PASS, duration_ms=(t6 - t0) * 1000.0,
                chat_id=chat_id, telegram_message_id=msg_id,
            )
        else:
            return TelegramDiagnostic(
                stage="http_request", status=PipelineStageStatus.FAIL, duration_ms=(t4 - t3) * 1000.0,
                chat_id=chat_id, http_status_code=http_status,
                error=f"HTTP {http_status}",
            )
    except Exception as e:
        t4 = time.monotonic()
        record_telegram_stage("HTTP Request", PipelineStageStatus.FAIL, (t4 - t3) * 1000.0, chat_id, error=str(e))
        return TelegramDiagnostic(
            stage="http_request", status=PipelineStageStatus.FAIL, duration_ms=(t4 - t3) * 1000.0,
            chat_id=chat_id, error=str(e),
        )
