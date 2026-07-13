"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type AnalyticsTrend } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { TrendingUp, Activity, AlertTriangle, Clock } from "lucide-react";

export default function AnalyticsPage() {
  const { data, isLoading, error } = useQuery<AnalyticsTrend[]>({
    queryKey: ["analyticsTrends"],
    queryFn: () => api.analyticsTrends(),
  });

  const trends = data ?? [];
  const last30 = trends.slice(-30);

  const latest = trends[trends.length - 1];

  const maxCollected = Math.max(...last30.map((t) => t.matches_collected), 1);
  const maxIncidents = Math.max(...last30.map((t) => t.incidents), 1);
  const maxLatency = Math.max(...last30.map((t) => t.avg_latency), 1);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Analytics</h1>

      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Matches Collected (Latest)"
          value={isLoading ? "—" : latest?.matches_collected ?? "—"}
          icon={<Activity className="h-4 w-4" />}
        />
        <StatCard
          title="Incidents (Latest)"
          value={isLoading ? "—" : latest?.incidents ?? "—"}
          icon={<AlertTriangle className="h-4 w-4" />}
          color={latest && latest.incidents > 0 ? "#ef4444" : undefined}
        />
        <StatCard
          title="Match Rate"
          value={isLoading ? "—" : latest ? `${latest.match_rate.toFixed(1)}%` : "—"}
          icon={<TrendingUp className="h-4 w-4" />}
        />
        <StatCard
          title="Avg Latency"
          value={isLoading ? "—" : latest ? `${latest.avg_latency.toFixed(1)} ms` : "—"}
          icon={<Clock className="h-4 w-4" />}
        />
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading analytics</p>
      ) : last30.length === 0 ? (
        <p className="text-sm text-slate-500">No analytics data</p>
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Daily Matches Discovered</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-1">
                {last30.map((t, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className="w-20 text-slate-500">{t.date}</span>
                    <div className="flex-1">
                      <div className="h-4 w-full overflow-hidden rounded bg-slate-800">
                        <div
                          className="h-full rounded bg-emerald-500 transition-all"
                          style={{ width: `${(t.matches_collected / maxCollected) * 100}%` }}
                        />
                      </div>
                    </div>
                    <span className="w-10 text-right font-mono text-slate-300">{t.matches_collected}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Incidents</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-1">
                  {last30.slice(-15).map((t, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <span className="w-20 text-slate-500">{t.date}</span>
                      <div className="flex-1">
                        <div className="h-3 w-full overflow-hidden rounded bg-slate-800">
                          <div
                            className={`h-full rounded transition-all ${t.incidents > 0 ? "bg-red-500" : "bg-emerald-500"}`}
                            style={{ width: `${(t.incidents / Math.max(maxIncidents, 1)) * 100}%` }}
                          />
                        </div>
                      </div>
                      <span className="w-6 text-right font-mono text-slate-300">{t.incidents}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Match Rate %</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-1">
                  {last30.slice(-15).map((t, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <span className="w-20 text-slate-500">{t.date}</span>
                      <div className="flex-1">
                        <div className="h-3 w-full overflow-hidden rounded bg-slate-800">
                          <div
                            className={`h-full rounded transition-all ${
                              t.match_rate >= 80 ? "bg-emerald-500" : t.match_rate >= 50 ? "bg-yellow-500" : "bg-red-500"
                            }`}
                            style={{ width: `${t.match_rate}%` }}
                          />
                        </div>
                      </div>
                      <span className="w-10 text-right font-mono text-slate-300">{t.match_rate.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Avg Latency (ms)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-1">
                  {last30.slice(-15).map((t, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <span className="w-20 text-slate-500">{t.date}</span>
                      <div className="flex-1">
                        <div className="h-3 w-full overflow-hidden rounded bg-slate-800">
                          <div
                            className={`h-full rounded bg-blue-500 transition-all`}
                            style={{ width: `${Math.min((t.avg_latency / maxLatency) * 100, 100)}%` }}
                          />
                        </div>
                      </div>
                      <span className="w-14 text-right font-mono text-slate-300">{t.avg_latency.toFixed(0)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
