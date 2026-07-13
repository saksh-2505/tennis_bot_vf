"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type MatchingSummary, type MatchingAttempt } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { DataTable } from "@/components/data/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/Tabs";
import { Select } from "@/components/ui/Select";
import { Link, AlertTriangle } from "lucide-react";
import { formatDate, formatPct } from "@/lib/utils";

const pageSizeOptions = [
  { label: "25", value: "25" },
  { label: "50", value: "50" },
  { label: "100", value: "100" },
];

export default function MatchingPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  const summary = useQuery<MatchingSummary>({
    queryKey: ["matchingSummary"],
    queryFn: () => api.matchingSummary(),
  });

  const unmatched = useQuery<MatchingAttempt[]>({
    queryKey: ["matchingUnmatched"],
    queryFn: () => api.matchingUnmatched(),
  });

  const attempts = useQuery<MatchingAttempt[]>({
    queryKey: ["matchingAttempts", page, pageSize],
    queryFn: () => api.matchingAttempts({ page: String(page), page_size: String(pageSize) }),
  });

  const s = summary.data;

  const unmatchedCols = [
    { field: "id", headerName: "ID", width: 80 },
    { field: "event_id", headerName: "Event ID", flex: 1 },
    { field: "player_a", headerName: "Player A", flex: 1.5 },
    { field: "player_b", headerName: "Player B", flex: 1.5 },
    { field: "source_provider", headerName: "Source", flex: 1 },
    { field: "timestamp", headerName: "Timestamp", valueFormatter: (p: any) => formatDate(p.value), flex: 1.5 },
  ];

  const attemptCols = [
    { field: "id", headerName: "ID", width: 80 },
    { field: "event_id", headerName: "Event ID", flex: 1 },
    { field: "player_a", headerName: "Player A", flex: 1.2 },
    { field: "player_b", headerName: "Player B", flex: 1.2 },
    {
      field: "confidence",
      headerName: "Confidence",
      width: 120,
      cellRenderer: (p: any) => {
        const v = p.value;
        if (v == null) return "—";
        const color = v >= 80 ? "text-emerald-400" : v >= 50 ? "text-yellow-400" : "text-red-400";
        return <span className={color}>{v.toFixed(1)}%</span>;
      },
    },
    {
      field: "matched",
      headerName: "Matched",
      width: 100,
      cellRenderer: (p: any) =>
        p.value ? <Badge variant="success">Yes</Badge> : <Badge variant="destructive">No</Badge>,
    },
    { field: "source_provider", headerName: "Source", flex: 1 },
    { field: "target_provider", headerName: "Target", flex: 1 },
    { field: "timestamp", headerName: "Timestamp", valueFormatter: (p: any) => formatDate(p.value), flex: 1.5 },
  ];

  const unmatchedCount = s?.unmatched_count ?? 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Market Matching</h1>

      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Total Attempts"
          value={summary.isLoading ? "—" : s?.total_attempts ?? "—"}
          icon={<Link className="h-4 w-4" />}
        />
        <StatCard
          title="Successful Matches"
          value={summary.isLoading ? "—" : s?.successful_matches ?? "—"}
          color="#22c55e"
        />
        <StatCard
          title="Unmatched"
          value={summary.isLoading ? "—" : unmatchedCount}
          color={unmatchedCount > 0 ? "#ef4444" : undefined}
        />
        <StatCard
          title="Match Rate"
          value={summary.isLoading ? "—" : formatPct(s?.match_rate ?? null)}
          color={s && s.match_rate >= 80 ? "#22c55e" : "#f59e0b"}
        />
      </div>

      {unmatchedCount > 0 && (
        <div className="flex items-center gap-2 rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-4 py-3">
          <AlertTriangle className="h-4 w-4 text-yellow-400" />
          <span className="text-sm text-yellow-300">
            {unmatchedCount} match{unmatchedCount > 1 ? "es" : ""} need market assignment
          </span>
        </div>
      )}

      <Tabs defaultValue="unmatched">
        <TabsList>
          <TabsTrigger value="unmatched">Unmatched Matches</TabsTrigger>
          <TabsTrigger value="attempts">Match Attempts</TabsTrigger>
        </TabsList>

        <TabsContent value="unmatched">
          {unmatched.isLoading ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : !unmatched.data || unmatched.data.length === 0 ? (
            <p className="text-sm text-slate-500">No unmatched matches</p>
          ) : (
            <DataTable rowData={unmatched.data} columnDefs={unmatchedCols} height={500} />
          )}
        </TabsContent>

        <TabsContent value="attempts">
          <div className="mb-3 flex items-center justify-end gap-3">
            <label className="text-xs text-slate-400">
              Page size:
              <Select
                options={pageSizeOptions}
                value={String(pageSize)}
                onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}
                className="ml-2 inline-block w-24"
              />
            </label>
          </div>
          {attempts.isLoading ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : !attempts.data || attempts.data.length === 0 ? (
            <p className="text-sm text-slate-500">No match attempts found</p>
          ) : (
            <DataTable rowData={attempts.data} columnDefs={attemptCols} height={500} />
          )}
          <div className="mt-3 flex justify-end gap-2">
            <button
              className="rounded border border-slate-700 px-3 py-1 text-xs text-slate-400 hover:bg-slate-800 disabled:opacity-50"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <button
              className="rounded border border-slate-700 px-3 py-1 text-xs text-slate-400 hover:bg-slate-800"
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
