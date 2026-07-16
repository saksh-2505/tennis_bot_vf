"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type AnalyticsTrend, type AnalyticsResponse } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { TrendingUp, Activity, CheckCircle, ShieldCheck } from "lucide-react";

export default function AnalyticsPage() {
  const { data, isLoading, error } = useQuery<AnalyticsResponse>({
    queryKey: ["analyticsTrends"],
    queryFn: () => api.analyticsTrends(),
  });

  const trends = data?.trends ?? [];
  const last30 = trends.slice(-30);
  const latest = trends[trends.length - 1];

  const maxDiscovered = Math.max(...last30.map((t) => t.matches_discovered ?? 0), 1);
  const maxTracked = Math.max(...last30.map((t) => t.matches_tracked ?? 0), 1);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Analytics</h1>

      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Discovered (Latest)"
          value={isLoading ? "—" : latest?.matches_discovered ?? "—"}
          icon={<Activity className="h-4 w-4" />}
        />
        <StatCard
          title="Tracked (Latest)"
          value={isLoading ? "—" : latest?.matches_tracked ?? "—"}
          icon={<TrendingUp className="h-4 w-4" />}
        />
        <StatCard
          title="Validation Pass"
          value={isLoading ? "—" : latest?.validation_pass_pct != null ? `${latest.validation_pass_pct}%` : "—"}
          icon={<CheckCircle className="h-4 w-4" />}
        />
        <StatCard
          title="Avg Quality Score"
          value={isLoading ? "—" : latest?.avg_quality_score != null ? String(latest.avg_quality_score) : "—"}
          icon={<ShieldCheck className="h-4 w-4" />}
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
                          style={{ width: `${((t.matches_discovered ?? 0) / maxDiscovered) * 100}%` }}
                        />
                      </div>
                    </div>
                    <span className="w-10 text-right font-mono text-slate-300">{t.matches_discovered ?? 0}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Matches Tracked</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-1">
                  {last30.slice(-15).map((t, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <span className="w-20 text-slate-500">{t.date}</span>
                      <div className="flex-1">
                        <div className="h-3 w-full overflow-hidden rounded bg-slate-800">
                          <div
                            className="h-full rounded bg-blue-500 transition-all"
                            style={{ width: `${((t.matches_tracked ?? 0) / Math.max(maxTracked, 1)) * 100}%` }}
                          />
                        </div>
                      </div>
                      <span className="w-8 text-right font-mono text-slate-300">{t.matches_tracked ?? 0}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Validation Pass Rate</CardTitle>
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
                              (t.validation_pass_pct ?? 0) >= 80
                                ? "bg-emerald-500"
                                : (t.validation_pass_pct ?? 0) >= 50
                                ? "bg-yellow-500"
                                : "bg-red-500"
                            }`}
                            style={{ width: `${t.validation_pass_pct ?? 0}%` }}
                          />
                        </div>
                      </div>
                      <span className="w-12 text-right font-mono text-slate-300">
                        {t.validation_pass_pct != null ? `${t.validation_pass_pct}%` : "—"}
                      </span>
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
