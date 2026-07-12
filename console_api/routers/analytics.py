from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from console_api.deps import get_db

router = APIRouter()


@router.get("/analytics/trends")
def analytics_trends(db: Session = Depends(get_db)):
    daily_tracked = db.execute(
        text(
            "SELECT created_at::date AS day, COUNT(*) "
            "FROM tracked_matches "
            "GROUP BY created_at::date "
            "ORDER BY day DESC LIMIT 90"
        )
    ).fetchall()

    daily_discovered = db.execute(
        text(
            "SELECT discovered_at::date AS day, COUNT(*) "
            "FROM flashscorefoundmatches "
            "GROUP BY discovered_at::date "
            "ORDER BY day DESC LIMIT 90"
        )
    ).fetchall()

    daily_completed = db.execute(
        text(
            "SELECT finalized_at::date AS day, "
            "COUNT(*), "
            "ROUND(AVG(CASE WHEN validation_passed THEN 100.0 ELSE 0.0 END)::numeric, 1), "
            "ROUND(AVG(quality_score)::numeric, 2) "
            "FROM completed_matches "
            "GROUP BY finalized_at::date "
            "ORDER BY day DESC LIMIT 90"
        )
    ).fetchall()

    # Build a dict keyed by date
    trends: dict[str, dict] = {}

    for r in daily_tracked:
        day = str(r[0])
        trends.setdefault(day, {})
        trends[day]["date"] = day
        trends[day]["matches_tracked"] = r[1]

    for r in daily_discovered:
        day = str(r[0])
        trends.setdefault(day, {})
        trends[day]["date"] = day
        trends[day]["matches_discovered"] = r[1]

    for r in daily_completed:
        day = str(r[0])
        trends.setdefault(day, {})
        trends[day]["date"] = day
        trends[day]["odds_collected"] = r[1]
        trends[day]["validation_pass_pct"] = float(r[2]) if r[2] is not None else 0.0
        trends[day]["avg_quality_score"] = float(r[3]) if r[3] is not None else None

    result = sorted(trends.values(), key=lambda x: x["date"], reverse=True)

    return {"trends": result}
