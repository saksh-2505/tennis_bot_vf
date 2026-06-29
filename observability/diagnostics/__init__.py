from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Callable

from observability.models import (
    PipelineResult,
    PipelineStageResult,
    PipelineStageStatus,
)

StageValidator = Callable[[], PipelineStageResult]


class PipelineDefinition:
    def __init__(self, name: str, stages: list[tuple[str, StageValidator]]) -> None:
        self.name = name
        self.stages = stages

    def validate(self) -> PipelineResult:
        started_at = datetime.now(timezone.utc)
        stage_results: list[PipelineStageResult] = []
        first_failure: str | None = None

        for stage_name, validator in self.stages:
            stage_start = time.monotonic()
            try:
                result = validator()
                elapsed = (time.monotonic() - stage_start) * 1000.0
                stage_results.append(PipelineStageResult(
                    stage_name=stage_name,
                    status=result.status,
                    duration_ms=elapsed,
                    error=result.error,
                    details=result.details,
                ))
                if result.status == PipelineStageStatus.FAIL and first_failure is None:
                    first_failure = stage_name
            except Exception as e:
                elapsed = (time.monotonic() - stage_start) * 1000.0
                stage_results.append(PipelineStageResult(
                    stage_name=stage_name,
                    status=PipelineStageStatus.FAIL,
                    duration_ms=elapsed,
                    error=str(e),
                ))
                if first_failure is None:
                    first_failure = stage_name

        ended_at = datetime.now(timezone.utc)
        overall = PipelineStageStatus.PASS if first_failure is None else PipelineStageStatus.FAIL

        return PipelineResult(
            pipeline_name=self.name,
            stages=stage_results,
            overall_status=overall,
            started_at=started_at,
            ended_at=ended_at,
            first_failure=first_failure,
        )


_pipelines: dict[str, PipelineDefinition] = {}


def register_pipeline(pipeline: PipelineDefinition) -> None:
    _pipelines[pipeline.name] = pipeline


def get_pipeline(name: str) -> PipelineDefinition | None:
    return _pipelines.get(name)


def get_all_pipelines() -> dict[str, PipelineDefinition]:
    return dict(_pipelines)


def validate_pipeline(name: str) -> PipelineResult | None:
    pipeline = _pipelines.get(name)
    if pipeline is None:
        return None
    return pipeline.validate()


def validate_platform() -> dict[str, PipelineResult]:
    results: dict[str, PipelineResult] = {}
    for name in list(_pipelines.keys()):
        result = validate_pipeline(name)
        if result:
            results[name] = result
    return results
