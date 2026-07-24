"use client";

import React, { useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api, type RepairSummary, type RepairHistoryItem } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { DataTable } from "@/components/data/DataTable";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Wrench, CheckCircle, XCircle, ExternalLink } from "lucide-react";
import { formatDate } from "@/lib/utils";

const gradeColor: Record<string, string> = {
  A: "text-emerald-400",
  B: "text-emerald-400",
  C: "text-yellow-400",
  D: "text-orange-400",
  F: "text-red-400",
};

export default function RepairPage() {
  const router = useRouter();

  const summary = useQuery<RepairSummary>({
    queryKey: ["repairsSummary"],
    queryFn: () => api.repairsSummary(),
  });

  // Previously dead: `repairsHistory()` was defined in lib/api.ts but never
  // called. Now surfaced as the per-match repair history table below, giving
  // the operator a real drill into which matches were re-processed.
  const history = useQuery<{ total: number; repairs: RepairHistoryItem[] }>({
    queryKey: ["repairsHistory"],
    queryFn: () => api.repairsHistory(),
  });

  const s = summary.data;
  const actions = s?.by_repair_action ?? [];
  const repairs = history.data?.repairs ?? [];
  const totalRepairs = history.data?.total ?? repairs.length;

  const onRowClicked = (e: any) => {
    const id = e.data?.tracked_match_id;
    if (id != null) router.push(`/matches/${id}`);
  };

  const repairCols = useMemo(() => [
    { field: "tracked_match_id", headerName: "Match ID", width: 100 },
    { field: "flashscore_match_id", headerName: "Flashscore ID", flex: 1.2 },
    { field: "tournament", headerName: "Tournament", flex: 1.5 },
    {
      field: "repair_actions",
      headerName: "Actions",
      flex: 1.5,
      cellRenderer: (p: any) => (p.value ? <Badge variant="warning">{String(p.value)}</Badge> : "—"),
    },
    {
      field: "repair_count",
      headerName: "Count",
      width: 80,
      valueFormatter: (p: any) => (p.value != null ? String(p.value) : "—"),
    },
    {
      field: "quality_grade",
      headerName: "Grade",
      width: 80,
      cellRenderer: (p: any) =>
        p.value ? <span className={gradeColor[p.value] ?? "text-slate-300"}>{p.value}</span> : "—",
    },
    {
      field: "validation_passed",
      headerName: "Valid",
      width: 80,
      cellRenderer: (p: any) =>
        p.value === true ? (
          <CheckCircle className="h-4 w-4 text-emerald-400" />
        ) : p.value === false ? (
          <XCircle className="h-4 w-4 text-red-400" />
        ) : (
          "—"
        ),
    },
    {
      field: "last_repaired_at",
      headerName: "Last Repaired",
      valueFormatter: (p: any) => formatDate(p.value),
      flex: 1.3,
    },
    {
      headerName: "Open",
      width: 80,
      cellRenderer: () => <ExternalLink className="h-3 w-3 text-emerald-400" />,
    },
  ], []);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Wrench className="h-6 w-6 text-slate-400" />
        <h1 className="text-2xl font-bold text-slate-100">Repair</h1>
      </div>

      {summary.isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : summary.error ? (
        <p className="text-sm text-red-400">Error loading repair data</p>
      ) : !s ? (
        <p className="text-sm text-slate-500">No repair data</p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4">
            <StatCard title="Total Repaired" value={s.total_repaired} icon={<Wrench className="h-4 w-4" />} />
            <StatCard
              title="Repair Actions"
              value={actions.length}
              color="#22c55e"
              icon={<CheckCircle className="h-4 w-4 text-emerald-400" />}
            />
          </div>

          {actions.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">By Repair Action</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {actions.map(({ action, count }) => (
                    <div key={action} className="flex items-center justify-between rounded border border-slate-800 p-3">
                      <span className="text-sm text-slate-300">{action}</span>
                      <Badge variant="outline">{count} matches</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Repair History ({totalRepairs})</CardTitle>
        </CardHeader>
        <CardContent>
          {history.isLoading ? (
            <p className="text-sm text-slate-500">Loading repair history...</p>
          ) : history.error ? (
            <p className="text-sm text-red-400">Error loading repair history</p>
          ) : repairs.length === 0 ? (
            <p className="text-sm text-slate-500">No repaired matches — click a row in the table to inspect a match.</p>
          ) : (
            <>
              <p className="mb-3 text-xs text-slate-500">
                Click a row to open the match detail page (with full scores/odds/incidents/repairs tabs).
              </p>
              <DataTable rowData={repairs} columnDefs={repairCols} height={550} onRowClicked={onRowClicked} />
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
