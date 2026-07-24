// Centralized React Query key factory — previously each page constructed
// literal-array keys inline (["overview"], ["incidents", params], ...).
// A factory prevents key drift, makes invalidation trivial, and stops two
// consumers using slightly-different arg shapes for the same endpoint.

export const queryKeys = {
  overview: () => ["overview"] as const,
  health: () => ["observabilityHealth"] as const,
  metrics: () => ["observabilityMetrics"] as const,

  matches: {
    live: () => ["matches", "live"] as const,
    detail: (id: number) => ["matches", "detail", id] as const,
    scores: (id: number) => ["matches", "scores", id] as const,
    odds: (id: number) => ["matches", "odds", id] as const,
    timeline: (id: number) => ["matches", "timeline", id] as const,
    points: (id: number) => ["matches", "points", id] as const,
    list: (params: Record<string, string>) => ["matches", "list", params] as const,
  },

  collectors: () => ["collectors"] as const,

  matching: {
    summary: () => ["matching", "summary"] as const,
    unmatched: () => ["matching", "unmatched"] as const,
    attempts: (params: Record<string, string>) => ["matching", "attempts", params] as const,
  },

  discovery: {
    summary: () => ["discovery", "summary"] as const,
    runs: () => ["discovery", "runs"] as const,
  },

  pipeline: () => ["pipeline", "status"] as const,

  incidents: {
    list: (params: Record<string, string>) => ["incidents", "list", params] as const,
    detail: (id: number) => ["incidents", "detail", id] as const,
  },

  quality: {
    distribution: () => ["quality", "distribution"] as const,
    failures: () => ["quality", "failures"] as const,
  },

  repairs: {
    summary: () => ["repairs", "summary"] as const,
    history: (params?: Record<string, string>) => ["repairs", "history", params ?? {}] as const,
  },

  validation: () => ["validation", "summary"] as const,

  registry: {
    summary: () => ["registry", "summary"] as const,
    players: (params: Record<string, string>) => ["registry", "players", params] as const,
  },

  db: {
    tables: () => ["db", "tables"] as const,
    table: (name: string) => ["db", "table", name] as const,
  },

  analytics: () => ["analytics", "trends"] as const,
  verification: () => ["verification", "history"] as const,

  search: (q: string) => ["search", q] as const,
  timeline: (params?: Record<string, string>) => ["timeline", params ?? {}] as const,
  reports: () => ["reports"] as const,
} as const;