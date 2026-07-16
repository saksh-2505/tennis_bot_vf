"use client";

import React from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api, type MatchDetail, type ScorePoint, type OddsPoint, type IncidentSummary } from "@/lib/api";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/Tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/data/DataTable";
import { ScoreTimeline } from "@/components/charts/ScoreTimeline";
import { formatDate } from "@/lib/utils";
import { ArrowLeft, Loader2, CheckCircle, XCircle } from "lucide-react";

export default function MatchDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = Number(params.id);

  const { data: match, isLoading, error } = useQuery<MatchDetail>({
    queryKey: ["matchDetail", id],
    queryFn: () => api.matchDetail(id),
    enabled: !isNaN(id),
  });

  const { data: scores } = useQuery<ScorePoint[]>({
    queryKey: ["matchScores", id],
    queryFn: () => api.matchScores(id),
    enabled: !isNaN(id),
  });

  const { data: odds } = useQuery<OddsPoint[]>({
    queryKey: ["matchOdds", id],
    queryFn: () => api.matchOdds(id),
    enabled: !isNaN(id),
  });

  const { data: incidents } = useQuery({
    queryKey: ["incidents"],
    queryFn: () => api.incidents(),
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

  const relatedIncidents = incidents?.items?.filter((inc: any) => inc.tracked_match_id === id) ?? [];
  const scorePoints = scores ?? match.scores ?? [];
  const oddsPoints = odds ?? match.odds ?? [];

  const statusBadge = (s: string) => {
    if (s === "LIVE") return <Badge variant="success">LIVE</Badge>;
    if (s === "FINISHED") return <Badge variant="outline">FINISHED</Badge>;
    if (s === "SCHEDULED") return <Badge className="bg-blue-600/20 text-blue-400 border-blue-600/30">SCHEDULED</Badge>;
    return <Badge variant="outline">{s}</Badge>;
  };

  const scoreCols = [
    { field: "timestamp", headerName: "Timestamp", valueFormatter: (p: any) => formatDate(p.value), flex: 2 },
    { field: "set_score_a", headerName: "Set A", width: 90 },
    { field: "set_score_b", headerName: "Set B", width: 90 },
    { field: "live_score_game_a", headerName: "Game A", width: 90 },
    { field: "live_score_game_b", headerName: "Game B", width: 90 },
    { field: "live_score_point", headerName: "Point A", width: 90 },
    { field: "live_score_point", headerName: "Point B", width: 90 },
    { field: "serving_player", headerName: "Server", width: 120 },
  ];

  const oddsCols = [
    { field: "timestamp", headerName: "Timestamp", valueFormatter: (p: any) => formatDate(p.value), flex: 2 },
    { field: "provider", headerName: "Provider", flex: 1 },
    { field: "odds_a", headerName: "Back A", valueFormatter: (p: any) => p.value?.toFixed(2) ?? "—", width: 100 },
    { field: "odds_b", headerName: "Back B", valueFormatter: (p: any) => p.value?.toFixed(2) ?? "—", width: 100 },
    { field: "market", headerName: "Market", flex: 1 },
  ];

  const incidentCols = [
    { field: "severity", headerName: "Severity", width: 100, cellRenderer: (p: any) => {
      const s = p.value;
      if (s === "CRITICAL" || s === "ERROR") return <Badge variant="destructive">{s}</Badge>;
      if (s === "WARNING") return <Badge variant="warning">{s}</Badge>;
      return <Badge variant="outline">{s}</Badge>;
    }},
    { field: "resolved", headerName: "Status", width: 100, cellRenderer: (p: any) =>
      p.value ? <Badge variant="success">Resolved</Badge> : <Badge variant="destructive">Open</Badge>
    },
    { field: "incident_type", headerName: "Category", flex: 1 },
    { field: "description", headerName: "Title", flex: 2 },
    { field: "timestamp", headerName: "First Detected", valueFormatter: (p: any) => formatDate(p.value), flex: 1.5 },
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
                      {match.live_score_point && ` ${match.live_score_point}-${match.live_score_point}`}
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
                    <span className="block text-xs text-slate-500">Collector</span>
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
            <CardHeader><CardTitle className="text-sm">Match Attempts</CardTitle></CardHeader>
            <CardContent>
              <p className="text-sm text-slate-500">
                No match attempt data available from API. Event ID: {match.flashscore_match_id || "N/A"}
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="repairs">
          <Card>
            <CardHeader><CardTitle className="text-sm">Repair History</CardTitle></CardHeader>
            <CardContent>
              <p className="text-sm text-slate-500">No repair data available for this match</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
