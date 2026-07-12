from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from console_api.deps import get_db

router = APIRouter()


@router.get("/validation/summary")
def validation_summary(db: Session = Depends(get_db)):
    from models.completed_match import CompletedMatch

    total = db.query(CompletedMatch).count()

    passed = db.query(CompletedMatch).filter(
        CompletedMatch.validation_passed.is_(True)
    ).count()
    failed = total - passed

    replay_ready = db.query(CompletedMatch).filter(
        CompletedMatch.ready_for_replay.is_(True)
    ).count()

    backtest_ready = db.query(CompletedMatch).filter(
        CompletedMatch.ready_for_backtesting.is_(True)
    ).count()

    return {
        "total_completed": total,
        "validation_passed": passed,
        "validation_failed": failed,
        "validation_pass_pct": round(passed / total * 100, 1) if total else 0.0,
        "ready_for_replay": replay_ready,
        "ready_for_backtesting": backtest_ready,
    }
