const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

async function fetchAPI<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(path, API_BASE);
  if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ─── Interfaces ────────────────────────────────────────────────

export interface PlatformOverview {
  live_matches: number;
  total_matches_today: number;
  collectors_running: number;
  db_size: string;
  incidents_today: number;
  repairs_needed: number;
  last_refresh: string | null;
  db_connected: boolean;
  uptime: string;
  version: string;
}

export interface MatchOverview {
  id: number;
  event_id: string;
  tournament: string;
  round: string;
  player_a: string;
  player_b: string;
  player_a_rank: number | null;
  player_b_rank: number | null;
  status: string;
  start_time: string | null;
  last_poll_time: string | null;
  set_score_a: number;
  set_score_b: number;
  game_score_a: number;
  game_score_b: number;
  point_score_a: string;
  point_score_b: string;
  odds_avg: number | null;
  odds_ev: number | null;
  quality_grade: string | null;
  matched: boolean;
  collector_name: string | null;
}

export interface MatchDetail extends MatchOverview {
  scores: ScorePoint[];
  odds: OddsPoint[];
  timeline: TimelineEvent[];
}

export interface ScorePoint {
  timestamp: string;
  set_score_a: number;
  set_score_b: number;
  game_score_a: number;
  game_score_b: number;
  point_score_a: string;
  point_score_b: string;
  serving_player: string | null;
}

export interface OddsPoint {
  timestamp: string;
  provider: string;
  odds_a: number;
  odds_b: number;
  market: string;
}

export interface TimelineEvent {
  timestamp: string;
  event_type: string;
  description: string;
  severity: string;
}

export interface CollectorStatus {
  name: string;
  type: string;
  running: boolean;
  last_run: string | null;
  matches_collected: number;
  errors: number;
  avg_latency: number | null;
  status: string;
}

export interface MatchingSummary {
  total_attempts: number;
  successful_matches: number;
  unmatched_count: number;
  match_rate: number;
  by_provider: Record<string, number>;
}

export interface MatchingAttempt {
  id: number;
  timestamp: string;
  event_id: string;
  player_a: string;
  player_b: string;
  source_provider: string;
  target_provider: string;
  matched: boolean;
  confidence: number | null;
  match_key: string | null;
}

export interface QualityDistribution {
  grade: string;
  count: number;
  percentage: number;
}

export interface QualityFailure {
  id: number;
  timestamp: string;
  event_id: string;
  check_type: string;
  field: string;
  expected: string | null;
  actual: string | null;
  severity: string;
  resolved: boolean;
}

export interface Incident {
  id: number;
  timestamp: string;
  event_id: string | null;
  incident_type: string;
  severity: string;
  description: string;
  resolved: boolean;
  resolved_at: string | null;
  resolution_note: string | null;
}

export interface RepairSummary {
  total_repairs: number;
  pending: number;
  in_progress: number;
  completed: number;
  failed: number;
  by_type: Record<string, number>;
}

export interface PipelineStatus {
  stage: string;
  status: string;
  last_run: string | null;
  items_processed: number;
  errors: number;
  duration_sec: number | null;
}

export interface Report {
  id: number;
  title: string;
  report_type: string;
  generated_at: string;
  format: string;
  size_bytes: number;
  status: string;
}

export interface AnalyticsTrend {
  date: string;
  matches_collected: number;
  incidents: number;
  match_rate: number;
  avg_latency: number;
}

export interface SearchResult {
  type: string;
  id: number;
  title: string;
  description: string;
  url: string;
}

export interface TimelineEntry {
  timestamp: string;
  event_type: string;
  description: string;
  source: string;
  match_id: number | null;
  event_id: string | null;
}

export interface DbTable {
  name: string;
  schema: string;
  row_count: number;
  size: string;
  last_vacuum: string | null;
}

export interface DbTableDetail {
  table_name: string;
  columns: { name: string; type: string; nullable: boolean }[];
  row_count: number;
  sample_rows: Record<string, any>[];
}

export interface RegistrySummary {
  total_entities: number;
  by_type: Record<string, number>;
  last_updated: string | null;
}

export interface DiscoverySummary {
  total_discovered: number;
  new_today: number;
  sources_active: number;
  last_scan: string | null;
  by_source: Record<string, number>;
}

export interface ValidationSummary {
  total_checks: number;
  passed: number;
  failed: number;
  pass_rate: number;
  by_check_type: Record<string, { passed: number; failed: number }>;
}

export interface VerificationHealthPoint {
  timestamp: string;
  health_score: number;
  checks_passed: number;
  checks_total: number;
}

export interface ObservabilityHealth {
  overall_status: string;
  components: { name: string; status: string; latency_ms: number | null; message: string | null }[];
}

// ─── API ──────────────────────────────────────────────────────

export const api = {
  overview: () => fetchAPI<PlatformOverview>('/api/overview'),
  liveMatches: () => fetchAPI<MatchOverview[]>('/api/matches/live'),
  matchDetail: (id: number) => fetchAPI<MatchDetail>(`/api/matches/${id}`),
  matchScores: (id: number) => fetchAPI<ScorePoint[]>('/api/matches/' + id + '/scores'),
  matchOdds: (id: number) => fetchAPI<OddsPoint[]>('/api/matches/' + id + '/odds'),
  matchTimeline: (id: number) => fetchAPI<TimelineEvent[]>('/api/matches/' + id + '/timeline'),
  searchMatches: (params: Record<string, string>) => fetchAPI<MatchOverview[]>('/api/matches', params),
  collectors: () => fetchAPI<CollectorStatus[]>('/api/collectors'),
  matchingSummary: () => fetchAPI<MatchingSummary>('/api/matching/summary'),
  matchingUnmatched: () => fetchAPI<MatchingAttempt[]>('/api/matching/unmatched'),
  matchingAttempts: (params: Record<string, string>) => fetchAPI<MatchingAttempt[]>('/api/matching/attempts', params),
  qualityDistribution: () => fetchAPI<QualityDistribution[]>('/api/quality/distribution'),
  qualityFailures: () => fetchAPI<QualityFailure[]>('/api/quality/failures'),
  incidents: (params?: Record<string, string>) => fetchAPI<Incident[]>('/api/incidents', params),
  incidentDetail: (id: number) => fetchAPI<Incident>('/api/incidents/' + id),
  repairsSummary: () => fetchAPI<RepairSummary>('/api/repairs/summary'),
  pipelineStatus: () => fetchAPI<PipelineStatus[]>('/api/pipeline/status'),
  reports: () => fetchAPI<Report[]>('/api/reports/all'),
  analyticsTrends: () => fetchAPI<AnalyticsTrend[]>('/api/analytics/trends'),
  search: (q: string) => fetchAPI<SearchResult[]>('/api/search', { q }),
  timeline: () => fetchAPI<TimelineEntry[]>('/api/timeline'),
  dbTables: () => fetchAPI<DbTable[]>('/api/db/tables'),
  dbTable: (name: string) => fetchAPI<DbTableDetail>('/api/db/table/' + name),
  registrySummary: () => fetchAPI<RegistrySummary>('/api/registry/summary'),
  discoverySummary: () => fetchAPI<DiscoverySummary>('/api/discovery/summary'),
  validationSummary: () => fetchAPI<ValidationSummary>('/api/validation/summary'),
  verificationHistory: () => fetchAPI<VerificationHealthPoint[]>('/api/verification/health-score-history'),
  observabilityHealth: () => fetchAPI<ObservabilityHealth>('/api/observability/health'),
};
