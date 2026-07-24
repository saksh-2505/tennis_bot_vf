"use client";

import React, { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type DiscoverySummary, type DiscoveryRun } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Compass, Satellite, History } from "lucide-react";
import { formatDate } from "@/lib/utils";

export default function DiscoveryPage() {
  const summary = useQuery<DiscoverySummary>({
    queryKey: ["discoverySummary"],
    queryFn: () => api.discoverySummary(),
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  // Previously dead: `discoveryRuns()` was exported from lib/api.ts but called
  // by nobody. Now surfaced as the "Recent Discovery Runs" section below.
  const runs = useQuery<DiscoveryRun[]>({
    queryKey: ["discoveryRuns"],
    queryFn: () => api.discoveryRuns(),
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  const s = summary.data;
  const fs_by_day = s?.flashscore_by_day ?? [];
  const bt_by_day = s?.bettingsite_by_day ?? [];
  // Last 30 days, oldest first (backend returns DESC; we want chronological-bottom-of-card).
  const fs_last30 = useMemo(() => fs_by_day.slice(0, 30).reverse(), [fs_by_day]);
  const bt_last30 = useMemo(() => bt_by_day.slice(0, 30).reverse(), [bt_by_day]);
  const maxFs = Math.max(...fs_last30.map((d) => d.count), 1);
  const maxBt = Math.max(...bt_last30.map((d) => d.count), 1);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Discovery</h1>

      <div className="grid grid-cols-2 gap-4">
        <StatCard
          title="Flashscore Matches"
          value={summary.isLoading ? "—" : s?.flashscore_total ?? "—"}
          icon={<Compass className="h-4 w-4" />}
        />
        <StatCard
          title="Betting Site Matches"
          value={summary.isLoading ? "—" : s?.bettingsite_total ?? "—"}
          icon={<Satellite className="h-4 w-4" />}
        />
      </div>

      {summary.isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : summary.error ? (
        <p className="text-sm text-red-400">Error loading discovery summary</p>
      ) : !s ? (
        <p className="text-sm text-slate-500">No discovery data</p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Flashscore — Daily Discoveries (last 30)</CardTitle>
              </CardHeader>
              <CardContent>
                {fs_last30.length === 0 ? (
                  <p className="text-sm text-slate-500">No daily data</p>
                ) : (
                  <div className="space-y-1">
                    {fs_last30.map((d) => (
                      <div key={d.date} className="flex items-center gap-2 text-xs">
                        <span className="w-20 text-slate-500">{d.date}</span>
                        <div className="flex-1">
                          <div className="h-3 w-full overflow-hidden rounded bg-slate-800">
                            <div
                              className="h-full rounded bg-emerald-500 transition-all"
                              style={{ width: `${(d.count / maxFs) * 100}%` }}
                            />
                          </div>
                        </div>
                        <span className="w-10 text-right font-mono text-slate-300">{d.count}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Betting Site — Daily Discoveries (last 30)</CardTitle>
              </CardHeader>
              <CardContent>
                {bt_last30.length === 0 ? (
                  <p className="text-sm text-slate-500">No daily data</p>
                ) : (
                  <div className="space-y-1">
                    {bt_last30.map((d) => (
                      <div key={d.date} className="flex items-center gap-2 text-xs">
                        <span className="w-20 text-slate-500">{d.date}</span>
                        <div className="flex-1">
                          <div className="h-3 w-full overflow-hidden rounded bg-slate-800">
                            <div
                              className="h-full rounded bg-blue-500 transition-all"
                              style={{ width: `${(d.count / maxBt) * 100}%` }}
                            />
                          </div>
                        </div>
                        <span className="w-10 text-right font-mono text-slate-300">{d.count}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <History className="h-4 w-4" />
                Recent Discovery Runs
              </CardTitle>
            </CardHeader>
            <CardContent>
              {runs.isLoading ? (
                <p className="text-sm text-slate-500">Loading runs...</p>
              ) : runs.error ? (
                <p className="text-sm text-red-400">Error loading discovery runs</p>
              ) : !runs.data || runs.data.length === 0 ? (
                <p className="text-sm text-slate-500">No recent discovery runs logged</p>
              ) : (
                <div className="space-y-2">
                  {runs.data.slice(0, 12).map((r, i) => (
                    <div key={i} className="flex items-start gap-3 rounded border border-slate-800 p-3">
                      <Badge variant="outline" className="text-xs">{r.level}</Badge>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-slate-300 truncate">{r.message}</p>
                        <p className="mt-1 text-xs text-slate-500">
                          {formatDate(r.timestamp)} · source: {r.source}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
