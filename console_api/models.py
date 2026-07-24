"""Pydantic API response models for the Developer Console."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class PlatformOverview(BaseModel):
    total_matches: int
    live_matches: int
    scheduled_matches: int
    finished_matches: int
    total_players: int
    total_incidents: int
    open_incidents: int
    total_score_ticks: int
    total_odds_ticks: int
    validation_pass_pct: float
    odds_coverage_pct: float
    replay_ready_pct: float
    avg_quality_score: float | None


class MatchOverview(BaseModel):
    id: int
    flashscore_match_id: str
    betting_market_id: str | None
    player1_name: str
    player2_name: str
    tournament: str
    status: str
    scheduled_start: datetime | None
    actual_finish: datetime | None
    live_score_set_a: int | None
    live_score_set_b: int | None
    live_score_game_a: int | None
    live_score_game_b: int | None
    live_score_point: str | None
    live_score_server: str | None
    live_odds_a: float | None
    live_odds_b: float | None
    last_score_poll: datetime | None
    last_odds_poll: datetime | None
    quality_grade: str | None
    quality_score: float | None


class MatchDetail(BaseModel):
    id: int
    flashscore_match_id: str
    betting_market_id: str | None
    player1_id: int | None
    player2_id: int | None
    player1_name: str
    player2_name: str
    tournament: str
    round: str | None
    surface: str | None
    status: str
    tracking_enabled: bool
    scheduled_start: datetime | None
    actual_finish: datetime | None
    match_duration_min: int | None
    market_assigned_at: datetime | None
    collection_started_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    # Live snapshot fields — parity with MatchOverview (TS `MatchDetail extends MatchOverview`).
    # Populated from the latest live_scores/live_odds + completed_matches.quality_*.
    live_score_set_a: int | None = None
    live_score_set_b: int | None = None
    live_score_game_a: int | None = None
    live_score_game_b: int | None = None
    live_score_point: str | None = None
    live_score_server: str | None = None
    live_odds_a: float | None = None
    live_odds_b: float | None = None
    last_score_poll: datetime | None = None
    last_odds_poll: datetime | None = None
    quality_grade: str | None = None
    quality_score: float | None = None

    completed: dict | None = None
    scores: list[dict] = []
    odds: list[dict] = []
    incidents: list[dict] = []
    repairs: list[dict] = []
    match_attempts: list[dict] = []


class CollectorStatus(BaseModel):
    name: str
    status: str
    last_poll: datetime | None
    records_count: int
    heartbeat_seconds_ago: float | None
    error_count: int
    success_rate: float


class IncidentSummary(BaseModel):
    id: int
    severity: str
    status: str
    category: str
    module: str
    title: str
    first_detected: datetime | None
    occurrence_count: int
    tracked_match_id: int | None


class RepairLog(BaseModel):
    match_id: int
    action: str
    repaired: bool
    reason: str
    timestamp: datetime | None


class QualityDistribution(BaseModel):
    grade: str
    count: int
    percentage: float


class PipelineStage(BaseModel):
    name: str
    status: str
    success_rate: float
    last_run: datetime | None
    affected_matches: int


class TraceSpan(BaseModel):
    span_id: str
    operation: str
    service: str
    start_time: datetime | None
    end_time: datetime | None
    status: str
    children: list["TraceSpan"] = []


class DiscoveryRun(BaseModel):
    run_at: datetime | None
    flashscore_discovered: int
    flashscore_saved: int
    bettingsite_discovered: int
    bettingsite_saved: int
    players_added: int
    registry_count: int
    duration_seconds: float
