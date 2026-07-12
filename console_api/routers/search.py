from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from console_api.deps import get_db

router = APIRouter()


@router.get("/search")
def search(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    limit: int = Query(30, le=100),
):
    from models.tracked_match import TrackedMatch
    from models.player import Player
    from incidents.models import Incident

    results: list[dict] = []

    # Tracked matches
    matches = (
        db.query(TrackedMatch)
        .filter(
            or_(
                TrackedMatch.player1_name.ilike(f"%{q}%"),
                TrackedMatch.player2_name.ilike(f"%{q}%"),
                TrackedMatch.tournament.ilike(f"%{q}%"),
                TrackedMatch.flashscore_match_id.ilike(f"%{q}%"),
            )
        )
        .order_by(TrackedMatch.id.desc())
        .limit(limit)
        .all()
    )
    for m in matches:
        results.append({
            "type": "match",
            "id": m.id,
            "label": f"{m.player1_name} vs {m.player2_name} ({m.tournament})",
            "match": {
                "flashscore_match_id": m.flashscore_match_id,
                "status": m.status,
                "betting_market_id": m.betting_market_id,
            },
        })

    # Players
    players = (
        db.query(Player)
        .filter(Player.full_name.ilike(f"%{q}%"))
        .order_by(Player.full_name)
        .limit(limit)
        .all()
    )
    for p in players:
        results.append({
            "type": "player",
            "id": p.player_id,
            "label": p.full_name,
            "match": {
                "nationality": p.nationality,
                "current_rank": p.current_rank,
                "gender": p.gender,
            },
        })

    # Incidents
    incidents = (
        db.query(Incident)
        .filter(Incident.title.ilike(f"%{q}%"))
        .order_by(Incident.last_detected_at.desc())
        .limit(limit)
        .all()
    )
    for inc in incidents:
        results.append({
            "type": "incident",
            "id": inc.incident_id,
            "label": inc.title,
            "match": {
                "severity": inc.severity,
                "status": inc.status,
                "category": inc.category,
            },
        })

    return {"results": results[:limit]}
