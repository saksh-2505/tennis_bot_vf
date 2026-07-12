"""Data repair, failure classification, and quality scoring.

Public API:
    run_repairs()       — run repairs on a single completed match
    run_repairs_on_all()— batch repair all eligible matches
    classify_failure()  — determine primary failure category
    compute_quality()   — compute A-F quality grade + scores
    score_all()         — batch quality score all matches
"""
from repair.classifier import FailureCategory, classify_all, classify_failure
from repair.engine import (
    RepairAction,
    REPAIR_HANDLERS,
    run_repairs,
    run_repairs_on_all,
)
from repair.quality import (
    QualityGrade,
    QualityScores,
    apply_quality_to_db,
    compute_quality,
    score_all,
)

__all__ = [
    "FailureCategory",
    "RepairAction",
    "REPAIR_HANDLERS",
    "classify_failure",
    "classify_all",
    "run_repairs",
    "run_repairs_on_all",
    "QualityGrade",
    "QualityScores",
    "compute_quality",
    "apply_quality_to_db",
    "score_all",
]
