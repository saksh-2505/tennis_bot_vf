"use client";

import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api, type PlatformOverview, type MatchOverview } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { MatchCard } from "@/components/data/MatchCard";
import { Activity, TrendingUp, ShieldCheck, AlertTriangle, Database, CheckCircle, Percent, ArrowRight } from "lucide-react";

const gradeColors: Record<string, string> = {
  A: "bg-emerald-500", B: "bg-blue-500", C: "bg-yellow-500",
  D: "bg-orange-500", F: "bg-red-500",
};

export default function DashboardPage() {
  const overview = useQuery<PlatformOverview>({
    queryKey: ["overview"],
    queryFn: () => api.overview(),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const liveMatches = useQuery<MatchOverview[]>({
    queryKey: ["liveMatches"],
    queryFn: () => api.liveMatches(),
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
  });

  const quality = useQuery({
    queryKey: ["qualityDistribution"],
    queryFn: () => api.qualityDistribution(),
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  const o = overview.data;
  const live = liveMatches.data ?? [];
  const q = quality.data;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Dashboard</h1>

      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Total Matches"
          value={o?.total_matches ?? "—"}
          icon={<Database className="h-4 w-4" />}
        />
        <StatCard
          title="Live Matches"
          value={o?.live_matches ?? "—"}
          icon={<Activity className="h-4 w-4 text-emerald-400" />}
          color="#22c55e"
        />
        <StatCard
          title="Finished Matches"
          value={o?.finished_matches ?? "—"}
          icon={<CheckCircle className="h-4 w-4" />}
        />
        <StatCard
          title="Total Players"
          value={o?.total_players ?? "—"}
          icon={<ShieldCheck className="h-4 w-4" />}
        />
      </div>

      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Open Incidents"
          value={o?.open_incidents ?? "—"}
          icon={<AlertTriangle className="h-4 w-4" />}
          color={Number(o?.open_incidents ?? 0) > 0 ? "#ef4444" : undefined}
        />
        <StatCard
          title="Validation Pass Rate"
          value={o?.validation_pass_pct != null ? `${o.validation_pass_pct}%` : "—"}
          icon={<CheckCircle className="h-4 w-4" />}
          trend={o?.validation_pass_pct != null && o.validation_pass_pct > 50 ? "up" : "down"}
        />
        <StatCard
          title="Odds Coverage"
          value={o?.odds_coverage_pct != null ? `${o.odds_coverage_pct}%` : "—"}
          icon={<Percent className="h-4 w-4" />}
        />
        <StatCard
          title="Avg Quality Score"
          value={o?.avg_quality_score != null ? String(o.avg_quality_score) : "—"}
          icon={<TrendingUp className="h-4 w-4" />}
          trend={o?.avg_quality_score != null && o.avg_quality_score > 50 ? "up" : "down"}
        />
      </div>

      <div className="grid grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-slate-300">
              Quality Distribution
              {q && (
                <Badge variant="outline" className="ml-2 text-xs">
                  {q.total_matches} total
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {quality.isLoading ? (
              <p className="text-sm text-slate-500">Loading...</p>
            ) : q?.distribution?.length ? (
              <div className="space-y-2 text-sm">
                {q.distribution.map(({ grade, count, percentage }) => (
                  <div key={grade} className="flex items-center gap-2">
                    <span className="w-4 text-xs font-mono text-slate-400">{grade}</span>
                    <div className="flex-1 h-4 rounded bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full rounded ${gradeColors[grade] || "bg-slate-600"} transition-all`}
                        style={{ width: `${Math.max(percentage, 2)}%` }}
                      />
                    </div>
                    <span className="w-12 text-right text-xs text-slate-400">{count}</span>
                    <span className="w-12 text-right text-xs text-slate-500">({percentage}%)</span>
                  </div>
                ))}
                {q.avg_quality_score != null && (
                  <div className="mt-3 pt-3 border-t border-slate-800 flex justify-between text-xs text-slate-400">
                    <span>Average Quality Score</span>
                    <span className="font-mono text-slate-200">{q.avg_quality_score.toFixed(1)}</span>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No completed matches yet</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium text-slate-300">
              Live Match Previews
              {live.length > 0 && (
                <Badge variant="success" className="ml-2">{live.length}</Badge>
              )}
            </CardTitle>
            {live.length > 5 && (
              <Link
                href="/matches/live"
                className="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300"
              >
                View all {live.length} <ArrowRight className="h-3 w-3" />
              </Link>
            )}
          </CardHeader>
          <CardContent>
            {liveMatches.isLoading ? (
              <p className="text-sm text-slate-500">Loading...</p>
            ) : live.length === 0 ? (
              <p className="text-sm text-slate-500">No live matches</p>
            ) : (
              <div className="flex flex-col gap-3">
                {live.slice(0, 5).map((m) => (
                  <MatchCard key={m.id} match={m} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
