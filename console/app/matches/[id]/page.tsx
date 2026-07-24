"use client";

import React, { useMemo } from "react";
import dynamic from "next/dynamic";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api, type MatchDetail } from "@/lib/api";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/Tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/data/DataTable";
import { formatDate } from "@/lib/utils";
import { ArrowLeft, Loader2, CheckCircle, XCircle } from "lucide-react";

// Code-split Recharts: ScoreTimeline pulls in `recharts` (~50 KB) and is only
// used on one tab of one page. Dynamic import keeps it out of the main bundle.
const ScoreTimeline = dynamic(
  () => import("@/components/charts/ScoreTimeline").then((m) => m.ScoreTimeline),
  { ssr: false, loading: () => <p className="text-sm text-slate-500">Loading chart…</p> }
);

export default function MatchDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = Number(params.id);

  const { data: match, isLoading, error } = useQuery<MatchDetail>({
    queryKey: ["matchDetail", id],
    queryFn: () => api.matchDetail(id),
    enabled: !isNaN(id),
    // Poll while LIVE — previously this page froze for live matches; the live
    // list kept polling at 5s but the match detail you'd opened went stale silently.
    refetchInterval: (query) => (query.state.data?.status === "LIVE" ? 10_000 : false),
    refetchIntervalInBackground: false,
    staleTime: 10_000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-400">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading match details...
      </div>
    );
  }

  if (error || !match) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Back
        </Button>
        <p className="text-sm text-red-400">Error loading match. It may not exist.</p>
      </div>
    );
  }

  // PERF: previously fetched three extra queries (`matchScores`, `matchOdds`,
  // and unparameterised `incidents` then filtered client-side). MatchDetail
  // already embeds `scores`, `odds`, and `incidents` (server-side filtered by
  // tracked_match_id). Drop the redundant round-trips + the full-incidents dump.
  const relatedIncidents = match.incidents ?? [];
  const scorePoints = match.scores ?? [];
  const oddsPoints = match.odds ?? [];

  const statusBadge = (s: string) => {
    if (s === "LIVE") return <Badge variant="success">LIVE</Badge>;
    if (s === "FINISHED") return <Badge variant="outline">FINISHED</Badge>;
    if (s === "SCHEDULED") return <Badge className="bg-blue-600/20 text-blue-400 border-blue-600/30">SCHEDULED</Badge>;
    return <Badge variant="outline">{s}</Badge>;
  };

  // Field names match ScorePoint (api.ts). Previous bug: used live_score_game_a/b,
  // live_score_point, serving_player — none of which exist on ScorePoint → blank cells.
  const scoreCols = [
    { field: "timestamp", headerName: "Timestamp", valueFormatter: (p: any) => formatDate(p.value), flex: 2 },
    { field: "set_score_a", headerName: "Set A", width: 90 },
    { field: "set_score_b", headerName: "Set B", width: 90 },
    { field: "game_score_a", headerName: "Game A", width: 90 },
    { field: "game_score_b", headerName: "Game B", width: 90 },
    { field: "point_score", headerName: "Point", width: 110 },
    { field: "server", headerName: "Server", width: 160 },
    { field: "is_tiebreak", headerName: "TB", width: 70, cellRenderer: (p: any) => (p.value ? "Y" : "") },
    { field: "match_finished", headerName: "Fin", width: 70, cellRenderer: (p: any) => (p.value ? "✓" : "") },
  ];

  // Field names match OddsPoint (api.ts). Previous bug: used provider/odds_a/odds_b/market
  // — none of which exist on OddsPoint → entire odds tab blank.
  const oddsCols = [
    { field: "timestamp", headerName: "Timestamp", valueFormatter: (p: any) => formatDate(p.value), flex: 2 },
    { field: "back_odds_a", headerName: "Back A", valueFormatter: (p: any) => (p.value != null ? p.value.toFixed(2) : "—"), width: 100 },
    { field: "back_odds_b", headerName: "Back B", valueFormatter: (p: any) => (p.value != null ? p.value.toFixed(2) : "—"), width: 100 },
    { field: "lay_odds_a", headerName: "Lay A", valueFormatter: (p: any) => (p.value != null ? p.value.toFixed(2) : "—"), width: 100 },
    { field: "lay_odds_b", headerName: "Lay B", valueFormatter: (p: any) => (p.value != null ? p.value.toFixed(2) : "—"), width: 100 },
    { field: "volume_a", headerName: "Vol A", valueFormatter: (p: any) => (p.value != null ? p.value.toLocaleString() : "—"), width: 110 },
    { field: "volume_b", headerName: "Vol B", valueFormatter: (p: any) => (p.value != null ? p.value.toLocaleString() : "—"), width: 110 },
  ];

  // Field names match IncidentSummary (api.ts). Previous bug: used incident_type,
  // resolved (bool), description, timestamp — none of which exist on IncidentSummary.
  const incidentCols = [
    { field: "severity", headerName: "Severity", width: 100, cellRenderer: (p: any) => {
      const s = p.value;
      if (s === "CRITICAL" || s === "ERROR") return <Badge variant="destructive">{s}</Badge>;
      if (s === "WARNING") return <Badge variant="warning">{s}</Badge>;
      return <Badge variant="outline">{s ?? "—"}</Badge>;
    }},
    { field: "status", headerName: "Status", width: 120, cellRenderer: (p: any) => {
      const s = p.value;
      if (s === "OPEN") return <Badge variant="destructive">OPEN</Badge>;
      if (s === "RESOLVED" || s === "CLOSED") return <Badge variant="success">{s}</Badge>;
      if (s === "ACKNOWLEDGED" || s === "RECOVERING") return <Badge variant="warning">{s}</Badge>;
      return <Badge variant="outline">{s ?? "—"}</Badge>;
    }},
    { field: "category", headerName: "Category", width: 160 },
    { field: "title", headerName: "Title", flex: 2 },
    { field: "module", headerName: "Module", width: 160 },
    { field: "first_detected", headerName: "First Detected", valueFormatter: (p: any) => formatDate(p.value), flex: 1.5 },
  ];

  // Match attempts (matcher audit log) — populated from MatchDetail.match_attempts
  // (backend already returns them; was previously a stub). Matches the matcher's
  // signal_scores/signal_reasons semantics; signal_* JSON blobs are kept out of the grid.
  const attemptCols = [
    { field: "betting_market_id", headerName: "Market ID", width: 150 },
    { field: "confidence_score", headerName: "Confidence", valueFormatter: (p: any) => (p.value != null ? `${(p.value * 100).toFixed(1)}%` : "—"), width: 110 },
    { field: "confidence_level", headerName: "Level", width: 110, cellRenderer: (p: any) => {
      const s = p.value;
      if (s === "REJECTED") return <Badge variant="destructive">REJECTED</Badge>;
      if (s === "HIGH") return <Badge variant="success">HIGH</Badge>;
      if (s === "MEDIUM") return <Badge variant="warning">MEDIUM</Badge>;
      if (s === "LOW") return <Badge variant="outline">LOW</Badge>;
      return <Badge variant="outline">{s ?? "—"}</Badge>;
    }},
    { field: "selected", headerName: "Selected", width: 90, cellRenderer: (p: any) => (p.value ? <CheckCircle className="h-4 w-4 text-emerald-400" /> : <XCircle className="h-4 w-4 text-slate-600" />) },
    { field: "rejected", headerName: "Rejected", width: 90, cellRenderer: (p: any) => (p.value ? <XCircle className="h-4 w-4 text-red-400" /> : <CheckCircle className="h-4 w-4 text-slate-600" />) },
    { field: "rejection_reason", headerName: "Rejection Reason", flex: 1.5 },
    { field: "created_at", headerName: "Created At", valueFormatter: (p: any) => formatDate(p.value), flex: 1.5 },
  ];

  // Repairs — populated from MatchDetail.repairs.
  const repairCols = [
    { field: "action", headerName: "Repair Action", flex: 3 },
    { field: "repaired_at", headerName: "Repaired At", valueFormatter: (p: any) => formatDate(p.value), flex: 2 },
  ];

  return (
    <div className="space-y-4">
      <Button variant="ghost" size="sm" onClick={() => router.back()}>
        <ArrowLeft className="mr-2 h-4 w-4" /> Back to Matches
      </Button>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">
            {match.player1_name} <span className="text-slate-500 text-lg">vs</span> {match.player2_name}
          </h1>
          <p className="text-sm text-slate-400">{match.tournament} — {match.round}</p>
        </div>
        <div className="flex items-center gap-2">
          {statusBadge(match.status)}
          {match.quality_grade && <Badge variant="outline">Q: {match.quality_grade}</Badge>}
        </div>
      </div>

      <Tabs defaultValue="overview">
        <TabsList className="flex-wrap">
          {[
            "overview", "scores", "odds", "timeline",
            "completed", "incidents", "matches", "repairs",
          ].map((tab) => (
            <TabsTrigger key={tab} value={tab}>
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="overview">
          <Card>
            <CardHeader><CardTitle className="text-sm">Match Info</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="block text-xs text-slate-500">Player A</span>
                  <span className="text-slate-200 font-medium">{match.player1_name}</span>
                </div>
                <div>
                  <span className="block text-xs text-slate-500">Player B</span>
                  <span className="text-slate-200 font-medium">{match.player2_name}</span>
                </div>
                <div>
                  <span className="block text-xs text-slate-500">Tournament</span>
                  <span className="text-slate-200">{match.tournament}</span>
                </div>
                <div>
                  <span className="block text-xs text-slate-500">Round</span>
                  <span className="text-slate-200">{match.round}</span>
                </div>
                <div>
                  <span className="block text-xs text-slate-500">Status</span>
                  {statusBadge(match.status)}
                </div>
                <div>
                  <span className="block text-xs text-slate-500">Start Time</span>
                  <span className="text-slate-200">{formatDate(match.scheduled_start)}</span>
                </div>
                <div>
                  <span className="block text-xs text-slate-500">Last Poll</span>
                  <span className="text-slate-200">{formatDate(match.last_score_poll)}</span>
                </div>
                <div>
                  <span className="block text-xs text-slate-500">Quality Grade</span>
                  <span className="text-slate-200">{match.quality_grade || "—"}</span>
                </div>
                {match.status === "LIVE" && (
                  <div className="col-span-2">
                    <span className="block text-xs text-slate-500">Live Score</span>
                    <span className="font-mono text-lg font-bold text-slate-100">
                      {match.live_score_set_a}-{match.live_score_set_b} ({match.live_score_game_a}-{match.live_score_game_b})
                      {/* live_score_point is already "X-Y" — show once, not doubled */}
                      {match.live_score_point && ` ${match.live_score_point}`}
                    </span>
                  </div>
                )}
                {match.live_odds_a != null && (
                  <div>
                    <span className="block text-xs text-slate-500">Odds A</span>
                    <span className="text-slate-200">{match.live_odds_a.toFixed(2)}</span>
                  </div>
                )}
                {match.live_odds_b != null && (
                  <div>
                    <span className="block text-xs text-slate-500">Odds B</span>
                    <span className="text-slate-200">{match.live_odds_b.toFixed(2)}</span>
                  </div>
                )}
                {match.live_score_server && (
                  <div>
                    <span className="block text-xs text-slate-500">Server</span>
                    <span className="text-slate-200">{match.live_score_server}</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="scores">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Score History ({scorePoints.length} ticks)</CardTitle>
            </CardHeader>
            <CardContent>
              {scorePoints.length === 0 ? (
                <p className="text-sm text-slate-500">No score data available</p>
              ) : (
                <DataTable rowData={scorePoints} columnDefs={scoreCols} height={500} />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="odds">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Odds History ({oddsPoints.length} ticks)</CardTitle>
            </CardHeader>
            <CardContent>
              {oddsPoints.length === 0 ? (
                <p className="text-sm text-slate-500">No odds data available</p>
              ) : (
                <DataTable rowData={oddsPoints} columnDefs={oddsCols} height={500} />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="timeline">
          <div className="space-y-4">
            {scorePoints.length > 0 ? (
              <ScoreTimeline scores={scorePoints} odds={oddsPoints} />
            ) : (
              <Card>
                <CardContent className="py-8">
                  <p className="text-sm text-slate-500">No score data for timeline visualization</p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        <TabsContent value="completed">
          <Card>
            <CardHeader><CardTitle className="text-sm">Completion Status</CardTitle></CardHeader>
            <CardContent>
              {match.status === "FINISHED" ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="rounded-lg border border-slate-800 bg-slate-800/50 p-3">
                      <span className="block text-xs text-slate-500">Final Set Score</span>
                      <span className="text-lg font-bold text-slate-100">{match.live_score_set_a}-{match.live_score_set_b}</span>
                    </div>
                    <div className="rounded-lg border border-slate-800 bg-slate-800/50 p-3">
                      <span className="block text-xs text-slate-500">Game Score</span>
                      <span className="text-lg font-bold text-slate-100">{match.live_score_game_a}-{match.live_score_game_b}</span>
                    </div>
                    <div className="rounded-lg border border-slate-800 bg-slate-800/50 p-3">
                      <span className="block text-xs text-slate-500">Score Ticks</span>
                      <span className="text-lg font-bold text-slate-100">{scorePoints.length}</span>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex items-center gap-2 rounded border border-slate-800 p-2 text-sm">
                      {match.betting_market_id ? (
                        <CheckCircle className="h-4 w-4 text-emerald-400" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-400" />
                      )}
                      <span className="text-slate-400">Market Assigned</span>
                      <Badge variant={match.betting_market_id ? "success" : "destructive"} className="ml-auto">
                        {match.betting_market_id ? "Yes" : "No"}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 rounded border border-slate-800 p-2 text-sm">
                      {match.quality_grade ? (
                        <CheckCircle className="h-4 w-4 text-emerald-400" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-400" />
                      )}
                      <span className="text-slate-400">Quality Graded</span>
                      <Badge variant={match.quality_grade ? "success" : "destructive"} className="ml-auto">
                        {match.quality_grade || "None"}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 rounded border border-slate-800 p-2 text-sm">
                      <CheckCircle className="h-4 w-4 text-emerald-400" />
                      <span className="text-slate-400">Odds Ticks</span>
                      <Badge variant="success" className="ml-auto">{oddsPoints.length}</Badge>
                    </div>
                    <div className="flex items-center gap-2 rounded border border-slate-800 p-2 text-sm">
                      <CheckCircle className="h-4 w-4 text-slate-600" />
                      <span className="text-slate-400">Live Score</span>
                      <span className="ml-auto text-xs text-slate-500">{match.live_score_server || "—"}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-slate-500">Match is not yet finished. Status: {match.status}</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="incidents">
          <Card>
            <CardHeader><CardTitle className="text-sm">Related Incidents ({relatedIncidents.length})</CardTitle></CardHeader>
            <CardContent>
              {relatedIncidents.length === 0 ? (
                <p className="text-sm text-slate-500">No incidents for this match</p>
              ) : (
                <DataTable rowData={relatedIncidents} columnDefs={incidentCols} height={400} />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="matches">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">
                Match Attempts ({match.match_attempts?.length ?? 0})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!match.match_attempts || match.match_attempts.length === 0 ? (
                <p className="text-sm text-slate-500">
                  No matching attempts for event {match.flashscore_match_id || "N/A"}.
                  This happens when the matcher engine never evaluated candidates for this match
                  — check <a className="text-emerald-400 hover:underline" href="/matching">/matching</a>{" "}
                  for unmatched matches.
                </p>
              ) : (
                <DataTable rowData={match.match_attempts} columnDefs={attemptCols} height={400} />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="repairs">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">
                Repair History ({match.repairs?.length ?? 0})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!match.repairs || match.repairs.length === 0 ? (
                <p className="text-sm text-slate-500">
                  No repair history for this match. Match was never re-processed by the repair engine
                  (quality grade A/B matches typically receive no repair actions).
                </p>
              ) : (
                <DataTable rowData={match.repairs} columnDefs={repairCols} height={300} />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
