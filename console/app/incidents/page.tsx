"use client";

import React, { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api, type IncidentDetail } from "@/lib/api";
import { DataTable } from "@/components/data/DataTable";
import { SeverityBadge } from "@/components/data/SeverityBadge";
import { Badge } from "@/components/ui/Badge";
import { Select } from "@/components/ui/Select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { SEVERITY_OPTIONS, INCIDENT_STATUS_OPTIONS } from "@/lib/constants";
import { formatDate } from "@/lib/utils";
import { AlertTriangle, X, Eye, ExternalLink } from "lucide-react";

export default function IncidentsPage() {
  const router = useRouter();
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const pageSize = 50;

  // Auto-open modal if '?incident_id=' is in the URL — enables deep links from
  // timeline, logs, match-detail pages, and shares.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("incident_id");
    if (id) setSelectedId(Number(id));
  }, []);

  const params: Record<string, string> = { page: String(page), page_size: String(pageSize) };
  if (severity) params.severity = severity;
  if (status) params.status = status;

  const { data, isLoading, error } = useQuery({
    queryKey: ["incidents", params],
    queryFn: () => api.incidents(params),
  });

  const { data: selectedIncident } = useQuery<IncidentDetail>({
    queryKey: ["incidentDetail", selectedId],
    queryFn: () => api.incidentDetail(selectedId!),
    enabled: selectedId != null,
  });

  const closeModal = () => setSelectedId(null);
  // Escape + backdrop click to dismiss modal (previously only the X button worked).
  useEffect(() => {
    if (selectedId == null) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") closeModal(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedId]);

  const incidents = data?.items ?? [];
  const total = data?.total ?? 0;

  // Memoize — AG Grid re-diffs columns each render otherwise; the cellRenderer
  // closures recreated here would also defeat React.memo in ScoreTimeline/etc.
  const cols = useMemo(() => [
    { field: "id", headerName: "ID", width: 80 },
    {
      field: "severity",
      headerName: "Severity",
      width: 110,
      cellRenderer: (p: any) => <SeverityBadge level={p.value} />,
    },
    {
      field: "status",
      headerName: "Status",
      width: 120,
      cellRenderer: (p: any) => {
        if (p.value === "RESOLVED" || p.value === "CLOSED")
          return <Badge variant="success">{p.value}</Badge>;
        if (p.value === "RECOVERING") return <Badge variant="info">{p.value}</Badge>;
        return <Badge variant="warning">{p.value}</Badge>;
      },
    },
    { field: "category", headerName: "Category", flex: 1 },
    { field: "module", headerName: "Module", flex: 1 },
    { field: "title", headerName: "Title", flex: 2 },
    { field: "first_detected", headerName: "First Detected", valueFormatter: (p: any) => formatDate(p.value), flex: 1.5 },
    {
      headerName: "Actions",
      width: 80,
      cellRenderer: (p: any) => (
        <button
          onClick={(e) => { e.stopPropagation(); setSelectedId(p.data.id); }}
          className="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300"
        >
          <Eye className="h-3 w-3" /> View
        </button>
      ),
    },
  ], []);

  // Bound the "Next" pagination button by total_pages so users can't page into emptiness.
  const totalPages = data?.total_pages ?? 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <AlertTriangle className="h-6 w-6 text-yellow-400" />
        <h1 className="text-2xl font-bold text-slate-100">Incidents</h1>
      </div>

      <div className="flex items-end gap-3">
        <div className="w-40">
          <label className="mb-1 block text-xs text-slate-400">Severity</label>
          <Select
            options={[...SEVERITY_OPTIONS]}
            value={severity}
            onChange={(e) => { setSeverity(e.target.value); setPage(1); }}
          />
        </div>
        <div className="w-40">
          <label className="mb-1 block text-xs text-slate-400">Status</label>
          <Select
            options={[...INCIDENT_STATUS_OPTIONS]}
            value={status}
            onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          />
        </div>
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading incidents</p>
      ) : incidents.length === 0 ? (
        <p className="text-sm text-slate-500">No incidents found</p>
      ) : (
        <DataTable rowData={incidents} columnDefs={cols} height={550} />
      )}

      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500">{total} incidents total · page {page}/{Math.max(totalPages, 1)}</span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            Next
          </Button>
        </div>
      </div>

      {selectedIncident && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          onClick={closeModal}
        >
          <Card className="w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-sm">Incident #{selectedIncident.id}</CardTitle>
              <button onClick={closeModal}>
                <X className="h-4 w-4 text-slate-400 hover:text-slate-200" />
              </button>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">Severity</span>
                  <Badge variant={selectedIncident.severity === "CRITICAL" || selectedIncident.severity === "ERROR" ? "destructive" : "warning"}>
                    {selectedIncident.severity}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Status</span>
                  <Badge variant={selectedIncident.status === "RESOLVED" ? "success" : "warning"}>
                    {selectedIncident.status}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Category</span>
                  <span className="text-slate-300">{selectedIncident.category}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Module</span>
                  <span className="text-slate-300">{selectedIncident.module}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">First Detected</span>
                  <span className="text-slate-300">{formatDate(selectedIncident.first_detected)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Last Detected</span>
                  <span className="text-slate-300">{formatDate(selectedIncident.last_detected_at)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Occurrences</span>
                  <span className="text-slate-300">{selectedIncident.occurrence_count}</span>
                </div>
                {selectedIncident.recovery_attempts > 0 && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Recovery Attempts</span>
                    <span className="text-slate-300">{selectedIncident.recovery_attempts}</span>
                  </div>
                )}
                {/* Cross-link → /matches/[id]. Previously `tracked_match_id` was
                    fetched but never displayed or linked — the biggest dead-end in the console. */}
                {selectedIncident.tracked_match_id != null && (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Match</span>
                    <button
                      onClick={() => router.push(`/matches/${selectedIncident.tracked_match_id}`)}
                      className="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300"
                    >
                      Match #{selectedIncident.tracked_match_id}
                      <ExternalLink className="h-3 w-3" />
                    </button>
                  </div>
                )}
                {/* Cross-link → /collectors. collector_name pinpoints which collector failed. */}
                {selectedIncident.collector_name && (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Collector</span>
                    <button
                      onClick={() => router.push("/collectors")}
                      className="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300"
                    >
                      {selectedIncident.collector_name}
                      <ExternalLink className="h-3 w-3" />
                    </button>
                  </div>
                )}
                <div>
                  <span className="block text-slate-500 mb-1">Title</span>
                  <p className="rounded bg-slate-800 p-2 text-slate-300">{selectedIncident.title}</p>
                </div>
                {selectedIncident.summary && (
                  <div>
                    <span className="block text-slate-500 mb-1">Summary</span>
                    <p className="rounded bg-slate-800 p-2 text-slate-300 whitespace-pre-wrap">{selectedIncident.summary}</p>
                  </div>
                )}
                {selectedIncident.resolved_at && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Resolved At</span>
                    <span className="text-slate-300">{formatDate(selectedIncident.resolved_at)}</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
