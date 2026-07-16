"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type MatchingSummary } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { DataTable } from "@/components/data/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/Tabs";
import { Select } from "@/components/ui/Select";
import { Link, AlertTriangle } from "lucide-react";
import { formatDate } from "@/lib/utils";

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

  const unmatched = useQuery({
    queryKey: ["matchingUnmatched"],
    queryFn: () => api.matchingUnmatched(),
  });

  const attempts = useQuery({
    queryKey: ["matchingAttempts", page, pageSize],
    queryFn: () => api.matchingAttempts({ page: String(page), page_size: String(pageSize) }),
  });

  const s = summary.data;
  const unmatchedMatches = unmatched.data?.matches ?? [];
  const attemptItems = attempts.data?.items ?? [];
  const attemptTotal = attempts.data?.total ?? 0;

  const unmatchedCols = [
    { field: "id", headerName: "ID", width: 80 },
    { field: "flashscore_match_id", headerName: "Flashscore ID", flex: 1 },
    { field: "player1_name", headerName: "Player 1", flex: 1.5 },
    { field: "player2_name", headerName: "Player 2", flex: 1.5 },
    { field: "tournament", headerName: "Tournament", flex: 1.5 },
    {
      field: "status",
      headerName: "Status",
      width: 120,
      cellRenderer: (p: any) => {
        if (p.value === "LIVE") return <Badge variant="success">LIVE</Badge>;
        if (p.value === "FINISHED") return <Badge variant="outline">FINISHED</Badge>;
        return <Badge variant="outline">{p.value}</Badge>;
      },
    },
  ];

  const attemptCols = [
    { field: "id", headerName: "ID", width: 80 },
    { field: "flashscore_match_id", headerName: "Flashscore ID", flex: 1 },
    { field: "player1_name", headerName: "Player 1", flex: 1.2 },
    { field: "player2_name", headerName: "Player 2", flex: 1.2 },
    {
      field: "confidence_score",
      headerName: "Confidence",
      width: 120,
      cellRenderer: (p: any) => {
        const v = p.value;
        if (v == null) return "—";
        const color = v >= 0.7 ? "text-emerald-400" : v >= 0.4 ? "text-yellow-400" : "text-red-400";
        return <span className={color}>{(v * 100).toFixed(1)}%</span>;
      },
    },
    {
      field: "selected",
      headerName: "Selected",
      width: 100,
      cellRenderer: (p: any) =>
        p.value ? <Badge variant="success">Yes</Badge> : <Badge variant="destructive">No</Badge>,
    },
    { field: "tournament", headerName: "Tournament", flex: 1 },
    { field: "confidence_level", headerName: "Level", width: 100 },
    { field: "created_at", headerName: "Timestamp", valueFormatter: (p: any) => formatDate(p.value), flex: 1.5 },
  ];

  const unmatchedCount = s?.without_market ?? 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Market Matching</h1>

      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Total Tracked"
          value={summary.isLoading ? "—" : s?.total_tracked ?? "—"}
          icon={<Link className="h-4 w-4" />}
        />
        <StatCard
          title="With Market"
          value={summary.isLoading ? "—" : s?.with_market ?? "—"}
          color="#22c55e"
        />
        <StatCard
          title="Without Market"
          value={summary.isLoading ? "—" : unmatchedCount}
          color={unmatchedCount > 0 ? "#ef4444" : undefined}
        />
        <StatCard
          title="Match Rate"
          value={summary.isLoading ? "—" : s ? `${s.matching_pct}%` : "—"}
          color={s && s.matching_pct >= 80 ? "#22c55e" : s && s.matching_pct >= 50 ? "#f59e0b" : "#ef4444"}
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
          <TabsTrigger value="unmatched">Unmatched ({unmatchedMatches.length})</TabsTrigger>
          <TabsTrigger value="attempts">Attempts ({attemptTotal})</TabsTrigger>
        </TabsList>

        <TabsContent value="unmatched">
          {unmatched.isLoading ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : unmatchedMatches.length === 0 ? (
            <p className="text-sm text-slate-500">No unmatched matches</p>
          ) : (
            <DataTable rowData={unmatchedMatches} columnDefs={unmatchedCols} height={500} />
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
          ) : attemptItems.length === 0 ? (
            <p className="text-sm text-slate-500">No match attempts</p>
          ) : (
            <DataTable rowData={attemptItems} columnDefs={attemptCols} height={500} />
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
