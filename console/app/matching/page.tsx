"use client";

import React, { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api, type MatchingSummary } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { DataTable } from "@/components/data/DataTable";
import { StatusBadge } from "@/components/data/StatusBadge";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/Tabs";
import { Select } from "@/components/ui/Select";
import { PAGE_SIZE_OPTIONS } from "@/lib/constants";
import { Link as LinkIcon, AlertTriangle } from "lucide-react";
import { formatDate } from "@/lib/utils";

const pageSizeOptions = [...PAGE_SIZE_OPTIONS];

export default function MatchingPage() {
  const router = useRouter();
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
  const attemptTotalPages = attempts.data?.total_pages ?? 1;

  // Row click → /matches/[id]. Unmatched matches are the most actionable queue
  // — previously a dead-end table. Attempt rows also link to their match.
  const onUnmatchedRowClicked = (e: any) => {
    const id = e.data?.id;
    if (id != null) router.push(`/matches/${id}`);
  };
  const onAttemptRowClicked = (e: any) => {
    const id = e.data?.id;
    // MatchAttempt rows from /matching/attempts have a numeric `id`; searchMatches
    // entries use the tracked_matches.id. Navigate to match detail when known.
    // (Backend `_match_attempts` in matches.py omits `id`; matching.py includes it.)
    if (id != null) router.push(`/matches/${id}`);
  };

  // Memoize — AG Grid re-processes columns on every render otherwise.
  const unmatchedCols = useMemo(() => [
    { field: "id", headerName: "ID", width: 80 },
    { field: "flashscore_match_id", headerName: "Flashscore ID", flex: 1 },
    { field: "player1_name", headerName: "Player 1", flex: 1.5 },
    { field: "player2_name", headerName: "Player 2", flex: 1.5 },
    { field: "tournament", headerName: "Tournament", flex: 1.5 },
    {
      field: "status",
      headerName: "Status",
      width: 120,
      cellRenderer: (p: any) => <StatusBadge status={p.value} />,
    },
  ], []);

  const attemptCols = useMemo(() => [
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
  ], []);

  const unmatchedCount = s?.without_market ?? 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Market Matching</h1>

      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Total Tracked"
          value={summary.isLoading ? "—" : s?.total_tracked ?? "—"}
          icon={<LinkIcon className="h-4 w-4" />}
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
            {unmatchedCount} match{unmatchedCount > 1 ? "es" : ""} need market assignment — click a row to inspect
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
            <DataTable
              rowData={unmatchedMatches}
              columnDefs={unmatchedCols}
              height={500}
              onRowClicked={onUnmatchedRowClicked}
            />
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
            <DataTable
              rowData={attemptItems}
              columnDefs={attemptCols}
              height={500}
              onRowClicked={onAttemptRowClicked}
            />
          )}
          <div className="mt-3 flex justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= attemptTotalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
            <span className="ml-3 self-center text-xs text-slate-500">
              page {page}/{Math.max(attemptTotalPages, 1)}
            </span>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
