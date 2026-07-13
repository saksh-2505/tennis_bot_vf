"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type PlatformOverview, type MatchOverview } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { MatchCard } from "@/components/data/MatchCard";
import { Activity, TrendingUp, ShieldCheck, AlertTriangle, Clock, Database } from "lucide-react";

const gradeColors: Record<string, string> = {
  A: "bg-emerald-500", B: "bg-blue-500", C: "bg-yellow-500",
  D: "bg-orange-500", F: "bg-red-500",
};

export default function DashboardPage() {
  const overview = useQuery<PlatformOverview>({
    queryKey: ["overview"],
    queryFn: () => api.overview(),
  });

  const liveMatches = useQuery<MatchOverview[]>({
    queryKey: ["liveMatches"],
    queryFn: () => api.liveMatches(),
    refetchInterval: 5000,
  });

  const o = overview.data;
  const live = liveMatches.data ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Dashboard</h1>

      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Total Matches Today"
          value={o?.total_matches_today ?? "—"}
          icon={<Activity className="h-4 w-4" />}
        />
        <StatCard
          title="Live Matches"
          value={o?.live_matches ?? "—"}
          icon={<Activity className="h-4 w-4 text-emerald-400" />}
          color="#22c55e"
        />
        <StatCard
          title="Collectors Running"
          value={o?.collectors_running ?? "—"}
          icon={<Database className="h-4 w-4" />}
        />
        <StatCard
          title="Incidents Today"
          value={o?.incidents_today ?? "—"}
          icon={<AlertTriangle className="h-4 w-4" />}
          color={Number(o?.incidents_today ?? 0) > 0 ? "#ef4444" : undefined}
        />
      </div>

      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="DB Size"
          value={o?.db_size ?? "—"}
          icon={<Database className="h-4 w-4" />}
        />
        <StatCard
          title="Repairs Needed"
          value={o?.repairs_needed ?? "—"}
          icon={<TrendingUp className="h-4 w-4" />}
          color={Number(o?.repairs_needed ?? 0) > 0 ? "#f59e0b" : undefined}
        />
        <StatCard
          title="Uptime"
          value={o?.uptime ?? "—"}
          icon={<Clock className="h-4 w-4" />}
        />
        <StatCard
          title="Version"
          value={o?.version ?? "—"}
          icon={<ShieldCheck className="h-4 w-4" />}
        />
      </div>

      <div className="grid grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-slate-300">Quality Distribution (placeholder)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm text-slate-400">
              <div className="flex items-center gap-2">
                <div className="h-3 w-24 rounded bg-emerald-500/50" />
                <span>Grade A</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-16 rounded bg-blue-500/50" />
                <span>Grade B</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-10 rounded bg-yellow-500/50" />
                <span>Grade C</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-6 rounded bg-orange-500/50" />
                <span>Grade D</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-4 rounded bg-red-500/50" />
                <span>Grade F</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-slate-300">
              Live Match Previews
              {live.length > 0 && (
                <Badge variant="success" className="ml-2">{live.length}</Badge>
              )}
            </CardTitle>
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
