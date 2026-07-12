from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from console_api.deps import get_db

router = APIRouter()

REPORT_NAMES = {
    "market_matching",
    "odds_coverage",
    "collection",
    "failure_distribution",
    "dataset_quality",
    "replay_readiness",
}


@router.get("/reports/all")
def reports_all(db: Session = Depends(get_db)):
    from reports.generator import generate_all_reports

    reports = generate_all_reports(db)
    return {name: _dataclass_to_dict(r) for name, r in reports.items()}


@router.get("/reports/{name}")
def reports_by_name(name: str, db: Session = Depends(get_db)):
    if name not in REPORT_NAMES:
        raise HTTPException(status_code=404, detail=f"Unknown report: {name}")

    from reports.generator import (
        generate_collection_report,
        generate_dataset_quality_report,
        generate_failure_distribution_report,
        generate_market_matching_report,
        generate_odds_coverage_report,
        generate_replay_readiness_report,
    )

    generators = {
        "market_matching": generate_market_matching_report,
        "odds_coverage": generate_odds_coverage_report,
        "collection": generate_collection_report,
        "failure_distribution": generate_failure_distribution_report,
        "dataset_quality": generate_dataset_quality_report,
        "replay_readiness": generate_replay_readiness_report,
    }

    report = generators[name](db)
    return _dataclass_to_dict(report)


def _dataclass_to_dict(obj):
    result = {}
    for k, v in asdict(obj).items():
        if k == "generated_at" and v:
            v = v.isoformat()
        result[k] = v
    return result
