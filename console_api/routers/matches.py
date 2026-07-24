"""Matches API — Live matches, match detail, score/odds history."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from console_api.deps import get_db, pagination_params
from console_api.models import MatchDetail, MatchOverview, PaginatedResponse

router = APIRouter()


@router.get("/matches/live", response_model=list[MatchOverview])
def get_live_matches(db: Session = Depends(get_db)):
    from models.tracked_match import TrackedMatch

    matches = (
        db.query(TrackedMatch)
        .filter(TrackedMatch.status == "LIVE")
        .all()
    )

    result = []
    for tm in matches:
        score = _latest_score(db, tm.id)
        odds = _latest_odds(db, tm.id)

        result.append(MatchOverview(
            id=tm.id,
            flashscore_match_id=tm.flashscore_match_id,
            betting_market_id=tm.betting_market_id,
            player1_name=tm.player1_name,
            player2_name=tm.player2_name,
            tournament=tm.tournament,
            status=tm.status,
            scheduled_start=tm.scheduled_start,
            actual_finish=tm.actual_finish,
            live_score_set_a=score.get("set_score_a"),
            live_score_set_b=score.get("set_score_b"),
            live_score_game_a=score.get("game_score_a"),
            live_score_game_b=score.get("game_score_b"),
            live_score_point=score.get("point_score"),
            live_score_server=score.get("server"),
            live_odds_a=odds.get("back_odds_a"),
            live_odds_b=odds.get("back_odds_b"),
            last_score_poll=score.get("timestamp"),
            last_odds_poll=odds.get("timestamp"),
            quality_grade=None,
            quality_score=None,
        ))

    return result


@router.get("/matches/{match_id}", response_model=MatchDetail)
def get_match_detail(match_id: int, db: Session = Depends(get_db)):
    from models.tracked_match import TrackedMatch

    tm = db.get(TrackedMatch, match_id)
    if tm is None:
        raise HTTPException(status_code=404, detail="Match not found")

    completed = _completed_data(db, match_id)
    scores = _score_history(db, match_id)
    odds_data = _odds_history(db, match_id)
    incidents = _match_incidents(db, match_id)
    repairs = _match_repairs(db, match_id)
    attempts = _match_attempts(db, match_id)
    latest_score = _latest_score(db, match_id)
    latest_odds = _latest_odds(db, match_id)

    return MatchDetail(
        id=tm.id,
        flashscore_match_id=tm.flashscore_match_id,
        betting_market_id=tm.betting_market_id,
        player1_id=tm.player1_id,
        player2_id=tm.player2_id,
        player1_name=tm.player1_name,
        player2_name=tm.player2_name,
        tournament=tm.tournament,
        round=tm.round,
        surface=tm.surface,
        status=tm.status,
        tracking_enabled=tm.tracking_enabled,
        scheduled_start=tm.scheduled_start,
        actual_finish=tm.actual_finish,
        match_duration_min=tm.match_duration_min,
        market_assigned_at=tm.market_assigned_at,
        collection_started_at=tm.collection_started_at,
        created_at=tm.created_at,
        updated_at=tm.updated_at,
        # Live snapshot — parity with MatchOverview (TS `MatchDetail extends MatchOverview`).
        live_score_set_a=latest_score.get("set_score_a"),
        live_score_set_b=latest_score.get("set_score_b"),
        live_score_game_a=latest_score.get("game_score_a"),
        live_score_game_b=latest_score.get("game_score_b"),
        live_score_point=latest_score.get("point_score"),
        live_score_server=latest_score.get("server"),
        live_odds_a=latest_odds.get("back_odds_a"),
        live_odds_b=latest_odds.get("back_odds_b"),
        last_score_poll=latest_score.get("timestamp"),
        last_odds_poll=latest_odds.get("timestamp"),
        # Quality from completed_matches (mirrors `quality_grade`/`quality_score` on MatchOverview).
        quality_grade=completed.get("quality_grade") if completed else None,
        quality_score=completed.get("quality_score") if completed else None,
        completed=completed,
        scores=scores,
        odds=odds_data,
        incidents=incidents,
        repairs=repairs,
        match_attempts=attempts,
    )


@router.get("/matches", response_model=PaginatedResponse)
def search_matches(
    db: Session = Depends(get_db),
    pagination: dict = Depends(pagination_params),
    status: str | None = Query(None),
    tournament: str | None = Query(None),
    player: str | None = Query(None),
    quality_grade: str | None = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
):
    from models.tracked_match import TrackedMatch
    from models.completed_match import CompletedMatch

    q = db.query(TrackedMatch)

    if status:
        q = q.filter(TrackedMatch.status == status.upper())
    if tournament:
        q = q.filter(TrackedMatch.tournament.ilike(f"%{tournament}%"))
    if player:
        q = q.filter(
            (TrackedMatch.player1_name.ilike(f"%{player}%"))
            | (TrackedMatch.player2_name.ilike(f"%{player}%"))
        )

    total = q.count()
    items = q.order_by(TrackedMatch.id.desc()).offset(offset).limit(limit).all()

    result = []
    # Batch-fetch completed_matches for the page in one query instead of N+1.
    ids = [tm.id for tm in items]
    cm_map: dict = {}
    if ids:
        cm_rows = (
            db.query(CompletedMatch)
            .filter(CompletedMatch.tracked_match_id.in_(ids))
            .all()
        )
        cm_map = {cm.tracked_match_id: cm for cm in cm_rows}

    for tm in items:
        cm = cm_map.get(tm.id)
        # quality_grade filter is honoured when set; previously had a tautology
        # `hasattr(tm,"id")` that always ran the per-row query (N+1 for every page load).
        if quality_grade and (cm is None or cm.quality_grade != quality_grade):
            continue

        result.append({
            "id": tm.id,
            "flashscore_match_id": tm.flashscore_match_id,
            "player1_name": tm.player1_name,
            "player2_name": tm.player2_name,
            "tournament": tm.tournament,
            "status": tm.status,
            "betting_market_id": tm.betting_market_id,
            "scheduled_start": tm.scheduled_start.isoformat() if tm.scheduled_start else None,
            "actual_finish": tm.actual_finish.isoformat() if tm.actual_finish else None,
            "duration_minutes": tm.match_duration_min,
            "quality_grade": cm.quality_grade if cm else None,
            "quality_score": cm.quality_score if cm else None,
        })

    return PaginatedResponse(
        items=result,
        total=total,
        page=pagination["page"],
        page_size=pagination["page_size"],
        total_pages=(total + limit - 1) // limit if limit else 0,
    )


@router.get("/matches/{match_id}/scores")
def get_match_scores(match_id: int, db: Session = Depends(get_db)):
    return _score_history(db, match_id)


@router.get("/matches/{match_id}/odds")
def get_match_odds(match_id: int, db: Session = Depends(get_db)):
    return _odds_history(db, match_id)


@router.get("/matches/{match_id}/timeline")
def get_match_timeline(match_id: int, db: Session = Depends(get_db)):
    scores = _score_history(db, match_id)
    odds_data = _odds_history(db, match_id)

    events: list[dict] = []
    for s in scores:
        events.append({**s, "type": "score"})
    for o in odds_data:
        events.append({**o, "type": "odds"})

    events.sort(key=lambda e: str(e.get("timestamp", "")))
    return events


@router.get("/matches/{match_id}/points")
def get_match_points(match_id: int, db: Session = Depends(get_db)):
    try:
        from models.live_point import LivePoint

        rows = (
            db.query(LivePoint)
            .filter(LivePoint.tracked_match_id == match_id)
            .order_by(LivePoint.timestamp.asc())
            .limit(1000)
            .all()
        )
        return [
            {
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "set_number": r.set_number,
                "game_number": r.game_number,
                "point_a": r.point_a,
                "point_b": r.point_b,
                "point_string": r.point_string,
                "server_name": r.server_name,
                "is_break_point": r.is_break_point,
                "is_set_point": r.is_set_point,
                "is_match_point": r.is_match_point,
                "is_tiebreak": r.is_tiebreak,
            }
            for r in rows
        ]
    except Exception:
        return []


def _latest_score(db: Session, match_id: int) -> dict:
    from models.live_score import LiveScore

    row = (
        db.query(LiveScore)
        .filter(LiveScore.tracked_match_id == match_id)
        .order_by(LiveScore.timestamp.desc())
        .first()
    )
    if row is None:
        return {}
    return {
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        "set_score_a": row.set_score_a,
        "set_score_b": row.set_score_b,
        "game_score_a": row.game_score_a,
        "game_score_b": row.game_score_b,
        "point_score": row.point_score,
        "server": row.server,
        "is_tiebreak": row.is_tiebreak,
        "match_finished": row.match_finished,
    }


def _latest_odds(db: Session, match_id: int) -> dict:
    from models.live_odds import LiveOdds

    row = (
        db.query(LiveOdds)
        .filter(LiveOdds.tracked_match_id == match_id)
        .order_by(LiveOdds.timestamp.desc())
        .first()
    )
    if row is None:
        return {}
    return {
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        "back_odds_a": row.back_odds_a,
        "back_odds_b": row.back_odds_b,
        "lay_odds_a": row.lay_odds_a,
        "lay_odds_b": row.lay_odds_b,
    }


def _score_history(db: Session, match_id: int, limit: int = 500) -> list[dict]:
    from models.live_score import LiveScore

    rows = (
        db.query(LiveScore)
        .filter(LiveScore.tracked_match_id == match_id)
        .order_by(LiveScore.timestamp.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "set_score_a": r.set_score_a,
            "set_score_b": r.set_score_b,
            "game_score_a": r.game_score_a,
            "game_score_b": r.game_score_b,
            "point_score": r.point_score,
            "server": r.server,
            "is_tiebreak": r.is_tiebreak,
            "match_finished": r.match_finished,
        }
        for r in rows
    ]


def _odds_history(db: Session, match_id: int, limit: int = 500) -> list[dict]:
    from models.live_odds import LiveOdds

    rows = (
        db.query(LiveOdds)
        .filter(LiveOdds.tracked_match_id == match_id)
        .order_by(LiveOdds.timestamp.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "back_odds_a": r.back_odds_a,
            "back_odds_b": r.back_odds_b,
            "lay_odds_a": r.lay_odds_a,
            "lay_odds_b": r.lay_odds_b,
            "volume_a": r.volume_a,
            "volume_b": r.volume_b,
        }
        for r in rows
    ]


def _completed_data(db: Session, match_id: int) -> dict | None:
    from models.completed_match import CompletedMatch

    cm = (
        db.query(CompletedMatch)
        .filter(CompletedMatch.tracked_match_id == match_id)
        .first()
    )
    if cm is None:
        return None

    return {
        "id": cm.id,
        "winner_player_id": cm.winner_player_id,
        "final_set_score": cm.final_set_score,
        "total_sets": cm.total_sets,
        "score_tick_count": cm.score_tick_count,
        "odds_tick_count": cm.odds_tick_count,
        "duration_minutes": cm.duration_minutes,
        "validation_passed": cm.validation_passed,
        "ready_for_replay": cm.ready_for_replay,
        "ready_for_backtesting": cm.ready_for_backtesting,
        "quality_grade": cm.quality_grade,
        "quality_score": cm.quality_score,
        "failure_category": cm.failure_category,
        "repair_count": cm.repair_count,
        "repair_actions": cm.repair_actions,
        "score_completeness_pct": cm.score_completeness_pct,
        "odds_completeness_pct": cm.odds_completeness_pct,
        "timeline_completeness_pct": cm.timeline_completeness_pct,
        "synchronization_score": cm.synchronization_score,
        "finalized_at": cm.finalized_at.isoformat() if cm.finalized_at else None,
    }


def _match_incidents(db: Session, match_id: int) -> list[dict]:
    try:
        from incidents.models import Incident

        rows = (
            db.query(Incident)
            .filter(Incident.tracked_match_id == match_id)
            .order_by(Incident.first_detected_at.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "id": r.incident_id,
                "severity": r.severity,
                "status": r.status,
                "category": r.category,
                "title": r.title,
                "first_detected": r.first_detected_at.isoformat() if r.first_detected_at else None,
                "occurrence_count": r.occurrence_count,
            }
            for r in rows
        ]
    except Exception:
        return []


def _match_repairs(db: Session, match_id: int) -> list[dict]:
    from models.completed_match import CompletedMatch

    cm = (
        db.query(CompletedMatch)
        .filter(CompletedMatch.tracked_match_id == match_id)
        .first()
    )
    if cm is None or not cm.repair_actions:
        return []
    return [{"action": cm.repair_actions, "repaired_at": cm.last_repaired_at.isoformat() if cm.last_repaired_at else None}]


def _match_attempts(db: Session, match_id: int) -> list[dict]:
    try:
        from models.tracked_match import TrackedMatch
        from matcher.models import MatchAttempt

        tm = db.get(TrackedMatch, match_id)
        if tm is None:
            return []

        rows = (
            db.query(MatchAttempt)
            .filter(MatchAttempt.flashscore_match_id == tm.flashscore_match_id)
            .order_by(MatchAttempt.created_at.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "betting_market_id": r.betting_market_id,
                "confidence_score": r.confidence_score,
                "confidence_level": r.confidence_level,
                "signal_scores": r.signal_scores,
                "signal_reasons": r.signal_reasons,
                "selected": r.selected,
                "rejected": r.rejected,
                "rejection_reason": r.rejection_reason,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    except Exception:
        return []
