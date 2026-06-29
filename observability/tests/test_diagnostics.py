from unittest.mock import patch

import pytest

from observability.diagnostics import (
    PipelineDefinition,
    PipelineStageResult,
    PipelineStageStatus,
    register_pipeline,
    get_pipeline,
    get_all_pipelines,
    validate_pipeline,
    validate_platform,
)


class TestPipelineDiagnostics:
    def teardown_method(self):
        from observability.diagnostics import _pipelines
        _pipelines.clear()

    def test_pipeline_definition(self):
        def pass_stage():
            return PipelineStageResult("pass_stage", PipelineStageStatus.PASS, 10.0)
        pipe = PipelineDefinition("test_pipe", [("Stage A", pass_stage)])
        register_pipeline(pipe)
        assert get_pipeline("test_pipe") is pipe

    def test_pipeline_all_pass(self):
        def stage1():
            return PipelineStageResult("s1", PipelineStageStatus.PASS, 5.0)
        def stage2():
            return PipelineStageResult("s2", PipelineStageStatus.PASS, 3.0)
        register_pipeline(PipelineDefinition("all_pass", [("S1", stage1), ("S2", stage2)]))
        result = validate_pipeline("all_pass")
        assert result is not None
        assert result.overall_status == PipelineStageStatus.PASS
        assert len(result.stages) == 2
        assert result.first_failure is None

    def test_pipeline_first_failure(self):
        def stage1():
            return PipelineStageResult("s1", PipelineStageStatus.PASS, 5.0)
        def stage2():
            return PipelineStageResult("s2", PipelineStageStatus.FAIL, 3.0, error="boom")
        def stage3():
            return PipelineStageResult("s3", PipelineStageStatus.PASS, 1.0)
        register_pipeline(PipelineDefinition("has_fail", [("S1", stage1), ("S2", stage2), ("S3", stage3)]))
        result = validate_pipeline("has_fail")
        assert result.overall_status == PipelineStageStatus.FAIL
        assert result.first_failure == "S2"
        assert result.stages[1].error == "boom"

    def test_pipeline_stage_exception(self):
        def failing_stage():
            raise ValueError("unexpected error")
        register_pipeline(PipelineDefinition("crash", [("Crash", failing_stage)]))
        result = validate_pipeline("crash")
        assert result.overall_status == PipelineStageStatus.FAIL
        assert result.first_failure == "Crash"
        assert "unexpected error" in result.stages[0].error

    def test_validate_nonexistent_pipeline(self):
        assert validate_pipeline("nonexistent") is None

    def test_validate_platform(self):
        def pass_stage():
            return PipelineStageResult("s", PipelineStageStatus.PASS, 1.0)
        register_pipeline(PipelineDefinition("p1", [("S", pass_stage)]))
        register_pipeline(PipelineDefinition("p2", [("S", pass_stage)]))
        results = validate_platform()
        assert "p1" in results
        assert "p2" in results

    def test_get_all_pipelines(self):
        def stub():
            return PipelineStageResult("s", PipelineStageStatus.PASS, 1.0)
        register_pipeline(PipelineDefinition("a", [("S", stub)]))
        all_p = get_all_pipelines()
        assert "a" in all_p
