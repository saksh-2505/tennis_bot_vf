from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from console_api.deps import get_db

router = APIRouter()


@router.get("/quality/distribution")
def quality_distribution(db: Session = Depends(get_db)):
    from models.completed_match import CompletedMatch

    total = db.query(CompletedMatch).count()

    grades = (
        db.query(
            CompletedMatch.quality_grade,
            func.count(),
        )
        .filter(CompletedMatch.quality_grade.isnot(None))
        .group_by(CompletedMatch.quality_grade)
        .all()
    )

    avg_score = (
        db.query(func.avg(CompletedMatch.quality_score))
        .filter(CompletedMatch.quality_score.isnot(None))
        .scalar()
    )

    return {
        "total_matches": total,
        "distribution": [
            {
                "grade": g,
                "count": c,
                "percentage": round(c / total * 100, 1) if total else 0.0,
            }
            for g, c in sorted(grades)
        ],
        "avg_quality_score": round(float(avg_score), 2) if avg_score else None,
    }


@router.get("/quality/failures")
def quality_failures(db: Session = Depends(get_db)):
    from models.completed_match import CompletedMatch

    rows = (
        db.query(
            CompletedMatch.failure_category,
            func.count(),
        )
        .filter(CompletedMatch.failure_category.isnot(None))
        .group_by(CompletedMatch.failure_category)
        .all()
    )

    total_failures = sum(c for _, c in rows)

    return {
        "total_failures": total_failures,
        "by_category": {cat or "unknown": cnt for cat, cnt in rows},
    }
