"""Report generation for dataset quality, market matching, and diagnostics."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class MarketMatchingReport:
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_tracked_matches: int = 0
    total_with_market: int = 0
    total_without_market: int = 0
    matching_pct: float = 0.0
    by_confidence: dict[str, int] = field(default_factory=dict)
    top_rejection_reasons: list[tuple[str, int]] = field(default_factory=list)
    historical_matching_pct: list[dict] = field(default_factory=list)


@dataclass
class OddsCoverageReport:
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_completed: int = 0
    with_odds: int = 0
    without_odds: int = 0
    coverage_pct: float = 0.0
    avg_odds_ticks: float = 0.0
    by_tournament: list[dict] = field(default_factory=list)


@dataclass
class CollectionReport:
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_completed: int = 0
    with_scores: int = 0
    avg_score_ticks: float = 0.0
    avg_odds_ticks: float = 0.0
    avg_duration_min: float = 0.0
    validation_pass_pct: float = 0.0
    by_day: list[dict] = field(default_factory=list)


@dataclass
class RepairReport:
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_scanned: int = 0
    repaired: int = 0
    unchanged: int = 0
    individual_fixes: int = 0
    by_action: dict[str, int] = field(default_factory=dict)


@dataclass
class FailureDistributionReport:
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_failures: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    unknown_count: int = 0


@dataclass
class DatasetQualityReport:
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_matches: int = 0
    by_grade: dict[str, int] = field(default_factory=dict)
    avg_quality_score: float = 0.0
    grade_distribution_pct: dict[str, float] = field(default_factory=dict)


@dataclass
class ReplayReadinessReport:
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total: int = 0
    ready: int = 0
    not_ready: int = 0
    readiness_pct: float = 0.0
    ready_matches: list[dict] = field(default_factory=list)


def generate_market_matching_report(session) -> MarketMatchingReport:
    from models.tracked_match import TrackedMatch

    total = session.query(TrackedMatch).count()
    with_market = session.query(TrackedMatch).filter(
        TrackedMatch.betting_market_id.isnot(None),
    ).count()
    without_market = total - with_market

    rpt = MarketMatchingReport(
        total_tracked_matches=total,
        total_with_market=with_market,
        total_without_market=without_market,
        matching_pct=round(with_market / total * 100, 1) if total else 0,
    )

    try:
        from matcher.models import MatchAttempt
        from sqlalchemy import func

        rpt.by_confidence = dict(
            session.query(
                MatchAttempt.confidence_level,
                func.count(),
            )
            .filter(MatchAttempt.selected.is_(True))
            .group_by(MatchAttempt.confidence_level)
            .all(),
        )

        top_rejections = (
            session.query(
                MatchAttempt.rejection_reason,
                func.count(),
            )
            .filter(MatchAttempt.rejected.is_(True))
            .group_by(MatchAttempt.rejection_reason)
            .order_by(func.count().desc())
            .limit(10)
            .all(),
        )
        rpt.top_rejection_reasons = [
            (r, c) for r, c in top_rejections[0]
        ] if top_rejections else []
    except Exception:
        pass

    return rpt


def generate_odds_coverage_report(session) -> OddsCoverageReport:
    from models.completed_match import CompletedMatch

    total = session.query(CompletedMatch).count()
    with_odds = session.query(CompletedMatch).filter(
        CompletedMatch.odds_tick_count > 0,
    ).count()

    avg_odds = (
        session.query(
            __import__("sqlalchemy").func.avg(CompletedMatch.odds_tick_count),
        )
        .filter(CompletedMatch.odds_tick_count > 0)
        .scalar()
    ) or 0.0

    rpt = OddsCoverageReport(
        total_completed=total,
        with_odds=with_odds,
        without_odds=total - with_odds,
        coverage_pct=round(with_odds / total * 100, 1) if total else 0,
        avg_odds_ticks=round(float(avg_odds), 1),
    )

    return rpt


def generate_collection_report(session) -> CollectionReport:
    from models.completed_match import CompletedMatch
    from sqlalchemy import func

    total = session.query(CompletedMatch).count()
    with_scores = session.query(CompletedMatch).filter(
        CompletedMatch.score_tick_count > 0,
    ).count()

    avg_scores = (
        session.query(func.avg(CompletedMatch.score_tick_count)).scalar()
    ) or 0.0
    avg_odds = (
        session.query(func.avg(CompletedMatch.odds_tick_count)).scalar()
    ) or 0.0
    avg_dur = (
        session.query(func.avg(CompletedMatch.duration_minutes)).scalar()
    ) or 0.0
    pass_pct = (
        session.query(CompletedMatch).filter(
            CompletedMatch.validation_passed.is_(True),
        ).count() / total * 100
    ) if total else 0

    rpt = CollectionReport(
        total_completed=total,
        with_scores=with_scores,
        avg_score_ticks=round(float(avg_scores), 1),
        avg_odds_ticks=round(float(avg_odds), 1),
        avg_duration_min=round(float(avg_dur), 1),
        validation_pass_pct=round(pass_pct, 1),
    )

    return rpt


def generate_failure_distribution_report(session) -> FailureDistributionReport:
    from models.completed_match import CompletedMatch

    failures = session.query(CompletedMatch).filter(
        CompletedMatch.validation_passed.is_(False),
    ).all()

    rpt = FailureDistributionReport(total_failures=len(failures))

    try:
        from models.completed_match import CompletedMatch
        from sqlalchemy import func

        cats = (
            session.query(
                CompletedMatch.failure_category,
                func.count(),
            )
            .filter(CompletedMatch.failure_category.isnot(None))
            .group_by(CompletedMatch.failure_category)
            .all()
        )
        rpt.by_category = {c or "none": cnt for c, cnt in cats}
        rpt.unknown_count = rpt.by_category.get("unknown", 0)
    except Exception:
        pass

    return rpt


def generate_dataset_quality_report(session) -> DatasetQualityReport:
    try:
        from models.completed_match import CompletedMatch
        from sqlalchemy import func

        total = session.query(CompletedMatch).count()
        grades_q = (
            session.query(
                CompletedMatch.quality_grade,
                func.count(),
            )
            .filter(CompletedMatch.quality_grade.isnot(None))
            .group_by(CompletedMatch.quality_grade)
            .all()
        )

        by_grade = {g or "?": cnt for g, cnt in grades_q}
        avg_score = (
            session.query(func.avg(CompletedMatch.quality_score))
            .filter(CompletedMatch.quality_score.isnot(None))
            .scalar()
        ) or 0.0

        rpt = DatasetQualityReport(
            total_matches=total,
            by_grade=by_grade,
            avg_quality_score=round(float(avg_score), 1),
            grade_distribution_pct={
                g: round(cnt / total * 100, 1)
                for g, cnt in by_grade.items()
            } if total else {},
        )

        return rpt
    except Exception:
        return DatasetQualityReport()


def generate_replay_readiness_report(session) -> ReplayReadinessReport:
    from models.completed_match import CompletedMatch

    total = session.query(CompletedMatch).count()
    ready = session.query(CompletedMatch).filter(
        CompletedMatch.ready_for_replay.is_(True),
    ).count()

    rpt = ReplayReadinessReport(
        total=total,
        ready=ready,
        not_ready=total - ready,
        readiness_pct=round(ready / total * 100, 1) if total else 0,
    )

    try:
        ready_matches = (
            session.query(CompletedMatch)
            .filter(CompletedMatch.ready_for_replay.is_(True))
            .order_by(CompletedMatch.quality_score.desc())
            .limit(20)
            .all()
        )
        rpt.ready_matches = [
            {
                "id": cm.tracked_match_id,
                "tournament": cm.tournament,
                "score_ticks": cm.score_tick_count,
                "odds_ticks": cm.odds_tick_count,
                "quality": cm.quality_score,
                "grade": cm.quality_grade,
            }
            for cm in ready_matches
        ]
    except Exception:
        pass

    return rpt


def generate_all_reports(session) -> dict:
    return {
        "market_matching": generate_market_matching_report(session),
        "odds_coverage": generate_odds_coverage_report(session),
        "collection": generate_collection_report(session),
        "failure_distribution": generate_failure_distribution_report(session),
        "dataset_quality": generate_dataset_quality_report(session),
        "replay_readiness": generate_replay_readiness_report(session),
    }


def print_report_summary(reports: dict) -> None:
    def _pct(label: str, pct: float) -> str:
        return f"{label}: {pct:.1f}%"

    mm = reports.get("market_matching")
    if mm:
        logger.info(_pct("Market matching", mm.matching_pct))

    oc = reports.get("odds_coverage")
    if oc:
        logger.info(
            "Odds coverage: %.1f%% (%d/%d matches, avg %.0f ticks)",
            oc.coverage_pct, oc.with_odds, oc.total_completed,
            oc.avg_odds_ticks,
        )

    cr = reports.get("collection")
    if cr:
        logger.info(
            "Collection: %.1f%% validation pass, avg %.0f score ticks, "
            "%.0f odds ticks, %.0f min",
            cr.validation_pass_pct, cr.avg_score_ticks,
            cr.avg_odds_ticks, cr.avg_duration_min,
        )

    dq = reports.get("dataset_quality")
    if dq and dq.by_grade:
        grades = ", ".join(f"{g}:{c}" for g, c in sorted(dq.by_grade.items()))
        logger.info(
            "Quality: avg %.1f — %s",
            dq.avg_quality_score, grades,
        )

    rr = reports.get("replay_readiness")
    if rr:
        logger.info(
            "Replay readiness: %.1f%% (%d/%d matches)",
            rr.readiness_pct, rr.ready, rr.total,
        )
