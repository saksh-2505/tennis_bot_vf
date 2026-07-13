"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type DiscoverySummary } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { formatDate } from "@/lib/utils";
import { Compass, PlusCircle, Satellite, Clock } from "lucide-react";

export default function DiscoveryPage() {
  const { data, isLoading, error } = useQuery<DiscoverySummary>({
    queryKey: ["discoverySummary"],
    queryFn: () => api.discoverySummary(),
  });

  const s = data;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Discovery</h1>

      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Total Discovered"
          value={isLoading ? "—" : s?.total_discovered ?? "—"}
          icon={<Compass className="h-4 w-4" />}
        />
        <StatCard
          title="New Today"
          value={isLoading ? "—" : s?.new_today ?? "—"}
          icon={<PlusCircle className="h-4 w-4 text-emerald-400" />}
          color="#22c55e"
        />
        <StatCard
          title="Active Sources"
          value={isLoading ? "—" : s?.sources_active ?? "—"}
          icon={<Satellite className="h-4 w-4" />}
        />
        <StatCard
          title="Last Scan"
          value={isLoading ? "—" : formatDate(s?.last_scan ?? null)}
          icon={<Clock className="h-4 w-4" />}
        />
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading discovery summary</p>
      ) : !s ? (
        <p className="text-sm text-slate-500">No discovery data</p>
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">By Source</CardTitle>
            </CardHeader>
            <CardContent>
              {Object.keys(s.by_source).length === 0 ? (
                <p className="text-sm text-slate-500">No source data</p>
              ) : (
                <div className="space-y-2">
                  {Object.entries(s.by_source).map(([source, count]) => (
                    <div key={source} className="flex items-center justify-between rounded border border-slate-800 p-3">
                      <span className="text-sm text-slate-300">{source}</span>
                      <span className="font-mono text-sm text-slate-100">{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">System Info</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="block text-xs text-slate-500">Total Discovered</span>
                  <span className="font-medium text-slate-200">{s.total_discovered}</span>
                </div>
                <div>
                  <span className="block text-xs text-slate-500">New Today</span>
                  <span className="font-medium text-slate-200">{s.new_today}</span>
                </div>
                <div>
                  <span className="block text-xs text-slate-500">Sources Active</span>
                  <span className="font-medium text-slate-200">{s.sources_active}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
