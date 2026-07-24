const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

async function fetchAPI<T>(path: string, params?: Record<string, string>): Promise<T> {
  let url: string;
  if (API_BASE) {
    const u = new URL(path, API_BASE);
    if (params) Object.entries(params).forEach(([k, v]) => u.searchParams.set(k, v));
    url = u.toString();
  } else {
    const searchParams = new URLSearchParams(params || {}).toString();
    url = path + (searchParams ? '?' + searchParams : '');
  }
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ─── Pagination ──────────────────────────────────────────────

export interface PaginatedResponse<T = Record<string, any>> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ─── Overview ─────────────────────────────────────────────────

export interface PlatformOverview {
  total_matches: number;
  live_matches: number;
  scheduled_matches: number;
  finished_matches: number;
  total_players: number;
  total_incidents: number;
  open_incidents: number;
  total_score_ticks: number;
  total_odds_ticks: number;
  validation_pass_pct: number;
  odds_coverage_pct: number;
  replay_ready_pct: number;
  avg_quality_score: number | null;
}

// ─── Matches ──────────────────────────────────────────────────

export interface MatchOverview {
  id: number;
  flashscore_match_id: string;
  betting_market_id: string | null;
  player1_name: string;
  player2_name: string;
  tournament: string;
  status: string;
  scheduled_start: string | null;
  actual_finish: string | null;
  live_score_set_a: number | null;
  live_score_set_b: number | null;
  live_score_game_a: number | null;
  live_score_game_b: number | null;
  live_score_point: string | null;
  live_score_server: string | null;
  live_odds_a: number | null;
  live_odds_b: number | null;
  last_score_poll: string | null;
  last_odds_poll: string | null;
  quality_grade: string | null;
  quality_score: number | null;
}

export interface MatchDetail extends MatchOverview {
  player1_id: number | null;
  player2_id: number | null;
  round: string | null;
  surface: string | null;
  tracking_enabled: boolean;
  match_duration_min: number | null;
  market_assigned_at: string | null;
  collection_started_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  completed: Record<string, any> | null;
  scores: ScorePoint[];
  odds: OddsPoint[];
  incidents: IncidentSummary[];
  repairs: Array<{ action: string; repaired_at: string | null }>;
  match_attempts: MatchAttempt[];
}

export interface ScorePoint {
  timestamp: string;
  set_score_a: number | null;
  set_score_b: number | null;
  game_score_a: number | null;
  game_score_b: number | null;
  point_score: string | null;
  server: string | null;
  is_tiebreak: boolean;
  match_finished: boolean;
}

export interface OddsPoint {
  timestamp: string;
  back_odds_a: number | null;
  back_odds_b: number | null;
  lay_odds_a: number | null;
  lay_odds_b: number | null;
  volume_a: number | null;
  volume_b: number | null;
}

// ─── Collectors ────────────────────────────────────────────────

export interface CollectorStatus {
  name: string;
  status: string;
  last_poll: string | null;
  records_count: number;
  heartbeat_seconds_ago: number | null;
}

// ─── Market Matching ──────────────────────────────────────────

export interface MatchingSummary {
  total_tracked: number;
  with_market: number;
  without_market: number;
  matching_pct: number;
  by_confidence: Record<string, number>;
}

export interface MatchAttempt {
  id?: number;
  flashscore_match_id?: string;
  betting_market_id?: string | null;
  player1_name?: string;
  player2_name?: string;
  tournament?: string;
  confidence_score?: number | null;
  confidence_level?: string | null;
  signal_scores?: any;
  signal_reasons?: any;
  selected?: boolean;
  rejected?: boolean;
  rejection_reason?: string | null;
  created_at?: string | null;
}

export interface UnmatchedMatch {
  id: number;
  flashscore_match_id: string;
  player1_name: string;
  player2_name: string;
  tournament: string;
  status: string;
  scheduled_start: string | null;
}

export interface UnmatchedResponse {
  total: number;
  offset: number;
  limit: number;
  matches: UnmatchedMatch[];
}

// ─── Discovery ─────────────────────────────────────────────────

export interface DiscoverySummary {
  flashscore_total: number;
  bettingsite_total: number;
  flashscore_by_day: Array<{ date: string; count: number }>;
  bettingsite_by_day: Array<{ date: string; count: number }>;
}

export interface DiscoveryRun {
  timestamp: string | null;
  level: string;
  source: string;
  message: string;
  details: any | null;
}

// ─── Pipeline ──────────────────────────────────────────────────

export interface PipelineStage {
  name: string;
  status: string;
  last_run: string | null;
}

export interface PipelineStatus {
  stages: PipelineStage[];
}

// ─── Incidents ─────────────────────────────────────────────────

export interface IncidentSummary {
  id: number;
  severity: string;
  status: string;
  category: string;
  module: string;
  title: string;
  first_detected: string | null;
  occurrence_count: number;
  tracked_match_id: number | null;
}

export interface IncidentDetail extends IncidentSummary {
  collector_name: string | null;
  summary: string | null;
  incident_hash: string | null;
  last_detected_at: string | null;
  resolved_at: string | null;
  recovery_attempts: number;
}

// ─── Quality ───────────────────────────────────────────────────

export interface QualityDistribution {
  total_matches: number;
  distribution: Array<{ grade: string; count: number; percentage: number }>;
  avg_quality_score: number | null;
}

export interface QualityFailures {
  total_failures: number;
  by_category: Record<string, number>;
}

// ─── Repair ────────────────────────────────────────────────────

export interface RepairSummary {
  total_repaired: number;
  by_repair_action: Array<{ action: string; count: number }>;
}

export interface RepairHistoryItem {
  tracked_match_id: number;
  flashscore_match_id: string;
  tournament: string;
  repair_actions: string | null;
  repair_count: number;
  last_repaired_at: string | null;
  quality_grade: string | null;
  validation_passed: boolean | null;
}

export interface RepairHistory {
  total: number;
  offset: number;
  limit: number;
  repairs: RepairHistoryItem[];
}

// ─── Validation ────────────────────────────────────────────────

export interface ValidationSummary {
  total_completed: number;
  validation_passed: number;
  validation_failed: number;
  validation_pass_pct: number;
  ready_for_replay: number;
  ready_for_backtesting: number;
}

// ─── Registry ──────────────────────────────────────────────────

export interface RegistrySummary {
  total: number;
  by_status: Record<string, number>;
}

export interface RegistryPlayer {
  player_id: number;
  full_name: string;
  nationality: string | null;
  age: number | null;
  gender: string | null;
  atp_or_wta: string | null;
  current_rank: number | null;
  career_high_rank: number | null;
  total_matches: number | null;
  total_wins: number | null;
  total_losses: number | null;
  career_win_percentage: number | null;
  plays: string | null;
  backhand: string | null;
}

// ─── Database ──────────────────────────────────────────────────

export interface DbTable {
  schema: string;
  table: string;
  row_count: number;
}

export interface DbTablesResponse {
  tables: DbTable[];
}

export interface DbTableDetail {
  table: string;
  columns: string[];
  offset: number;
  limit: number;
  rows: Record<string, any>[];
}

// ─── Analytics ─────────────────────────────────────────────────

export interface AnalyticsTrend {
  date: string;
  matches_tracked?: number;
  matches_discovered?: number;
  odds_collected?: number;
  validation_pass_pct?: number;
  avg_quality_score?: number | null;
}

export interface AnalyticsResponse {
  trends: AnalyticsTrend[];
}

// ─── Search ────────────────────────────────────────────────────

export interface SearchResult {
  type: string;
  id: number | string;
  label: string;
  match?: Record<string, any>;
}

export interface SearchResponse {
  results: SearchResult[];
}

// ─── Timeline ──────────────────────────────────────────────────

export interface TimelineEntry {
  timestamp: string | null;
  event_id: number;
  level: string;
  source: string;
  message: string;
  details: any | null;
  incident_id: number | null;
  tracked_match_id: number | null;
}

// ─── Verification ──────────────────────────────────────────────

export interface VerificationHistoryResponse {
  history: Array<Record<string, any>>;
}

// ─── Observability ─────────────────────────────────────────────

export interface ObservabilityHealth {
  db: boolean;
  version: string;
}

export interface ObservabilityMetrics {
  events_by_level: Record<string, number>;
  events_by_source: Record<string, number>;
  recent_events: Array<{
    timestamp: string | null;
    level: string;
    source: string;
    message: string;
  }>;
}

// ─── Reports ───────────────────────────────────────────────────

export interface ReportsResponse {
  market_matching: Record<string, any>;
  odds_coverage: Record<string, any>;
  collection: Record<string, any>;
  failure_distribution: Record<string, any>;
  dataset_quality: Record<string, any>;
  replay_readiness: Record<string, any>;
}

// ─── API functions ─────────────────────────────────────────────

export const api = {
  overview: () => fetchAPI<PlatformOverview>('/api/overview'),
  liveMatches: () => fetchAPI<MatchOverview[]>('/api/matches/live'),
  matchDetail: (id: number) => fetchAPI<MatchDetail>(`/api/matches/${id}`),
  matchScores: (id: number) => fetchAPI<ScorePoint[]>(`/api/matches/${id}/scores`),
  matchOdds: (id: number) => fetchAPI<OddsPoint[]>(`/api/matches/${id}/odds`),
  matchTimeline: (id: number) => fetchAPI<Record<string, any>[]>(`/api/matches/${id}/timeline`),
  matchPoints: (id: number) => fetchAPI<Record<string, any>[]>(`/api/matches/${id}/points`),
  searchMatches: (params: Record<string, string>) =>
    fetchAPI<PaginatedResponse>('/api/matches', params),

  collectors: () => fetchAPI<CollectorStatus[]>('/api/collectors'),

  matchingSummary: () => fetchAPI<MatchingSummary>('/api/matching/summary'),
  matchingUnmatched: () => fetchAPI<UnmatchedResponse>('/api/matching/unmatched'),
  matchingAttempts: (params?: Record<string, string>) =>
    fetchAPI<PaginatedResponse<MatchAttempt>>('/api/matching/attempts', params),

  discoverySummary: () => fetchAPI<DiscoverySummary>('/api/discovery/summary'),
  discoveryRuns: () => fetchAPI<DiscoveryRun[]>('/api/discovery/runs'),

  pipelineStatus: () => fetchAPI<PipelineStatus>('/api/pipeline/status'),

  incidents: (params?: Record<string, string>) =>
    fetchAPI<PaginatedResponse<IncidentSummary>>('/api/incidents', params),
  incidentDetail: (id: number) => fetchAPI<IncidentDetail>(`/api/incidents/${id}`),

  qualityDistribution: () => fetchAPI<QualityDistribution>('/api/quality/distribution'),
  qualityFailures: () => fetchAPI<QualityFailures>('/api/quality/failures'),

  repairsSummary: () => fetchAPI<RepairSummary>('/api/repairs/summary'),
  repairsHistory: (params?: Record<string, string>) =>
    fetchAPI<RepairHistory>('/api/repairs/history', params),

  validationSummary: () => fetchAPI<ValidationSummary>('/api/validation/summary'),

  registrySummary: () => fetchAPI<RegistrySummary>('/api/registry/summary'),
  registryPlayers: (params?: Record<string, string>) =>
    fetchAPI<PaginatedResponse<RegistryPlayer>>('/api/registry/players', params),

  dbTables: () => fetchAPI<DbTablesResponse>('/api/db/tables'),
  dbTable: (name: string) => fetchAPI<DbTableDetail>('/api/db/table/' + name),

  analyticsTrends: () => fetchAPI<AnalyticsResponse>('/api/analytics/trends'),

  search: (q: string) => fetchAPI<SearchResponse>('/api/search', { q }),

  timeline: (params?: Record<string, string>) =>
    fetchAPI<PaginatedResponse<TimelineEntry>>('/api/timeline', params),

  verificationHistory: () => fetchAPI<VerificationHistoryResponse>('/api/verification/health-score-history'),

  observabilityHealth: () => fetchAPI<ObservabilityHealth>('/api/observability/health'),
  observabilityMetrics: () => fetchAPI<ObservabilityMetrics>('/api/observability/metrics'),

  reports: () => fetchAPI<ReportsResponse>('/api/reports/all'),
  reportByName: (name: string) => fetchAPI<Record<string, any>>(`/api/reports/${name}`),
};
