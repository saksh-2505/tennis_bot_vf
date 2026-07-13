"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type Incident } from "@/lib/api";
import { DataTable } from "@/components/data/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Select } from "@/components/ui/Select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { formatDate } from "@/lib/utils";
import { AlertTriangle, X, Eye } from "lucide-react";

const severityOptions = [
  { label: "All", value: "" },
  { label: "CRITICAL", value: "CRITICAL" },
  { label: "ERROR", value: "ERROR" },
  { label: "WARNING", value: "WARNING" },
  { label: "INFO", value: "INFO" },
];

const statusOptions = [
  { label: "All", value: "" },
  { label: "Open", value: "false" },
  { label: "Resolved", value: "true" },
];

export default function IncidentsPage() {
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const pageSize = 50;

  const params: Record<string, string> = { page: String(page), page_size: String(pageSize) };
  if (severity) params.severity = severity;
  if (status) params.resolved = status;

  const { data, isLoading, error } = useQuery<Incident[]>({
    queryKey: ["incidents", params],
    queryFn: () => api.incidents(params),
  });

  const incidents = data ?? [];

  const cols = [
    { field: "id", headerName: "ID", width: 80 },
    {
      field: "severity",
      headerName: "Severity",
      width: 110,
      cellRenderer: (p: any) => {
        const s = p.value;
        if (s === "CRITICAL") return <Badge variant="destructive">CRITICAL</Badge>;
        if (s === "ERROR") return <Badge variant="destructive">ERROR</Badge>;
        if (s === "WARNING") return <Badge variant="warning">WARNING</Badge>;
        return <Badge variant="outline">{s}</Badge>;
      },
    },
    {
      field: "resolved",
      headerName: "Status",
      width: 100,
      cellRenderer: (p: any) =>
        p.value ? <Badge variant="success">Resolved</Badge> : <Badge variant="warning">Open</Badge>,
    },
    { field: "incident_type", headerName: "Category", flex: 1 },
    { field: "description", headerName: "Title", flex: 2 },
    { field: "timestamp", headerName: "First Detected", valueFormatter: (p: any) => formatDate(p.value), flex: 1.5 },
    {
      headerName: "Actions",
      width: 90,
      cellRenderer: (p: any) => (
        <button
          onClick={(e) => { e.stopPropagation(); setSelectedIncident(p.data); }}
          className="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300"
        >
          <Eye className="h-3 w-3" /> View
        </button>
      ),
    },
  ];

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
            options={severityOptions}
            value={severity}
            onChange={(e) => { setSeverity(e.target.value); setPage(1); }}
          />
        </div>
        <div className="w-40">
          <label className="mb-1 block text-xs text-slate-400">Status</label>
          <Select
            options={statusOptions}
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
        <DataTable
          rowData={incidents}
          columnDefs={cols}
          height={550}
        />
      )}

      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500">{incidents.length} incidents</span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <Button variant="outline" size="sm" onClick={() => setPage((p) => p + 1)}>
            Next
          </Button>
        </div>
      </div>

      {selectedIncident && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <Card className="w-full max-w-lg">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-sm">Incident #{selectedIncident.id}</CardTitle>
              <button onClick={() => setSelectedIncident(null)}>
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
                  {selectedIncident.resolved ? (
                    <Badge variant="success">Resolved</Badge>
                  ) : (
                    <Badge variant="warning">Open</Badge>
                  )}
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Type</span>
                  <span className="text-slate-300">{selectedIncident.incident_type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Event ID</span>
                  <span className="text-slate-300">{selectedIncident.event_id || "—"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">First Detected</span>
                  <span className="text-slate-300">{formatDate(selectedIncident.timestamp)}</span>
                </div>
                <div>
                  <span className="block text-slate-500 mb-1">Description</span>
                  <p className="rounded bg-slate-800 p-2 text-slate-300">{selectedIncident.description}</p>
                </div>
                {selectedIncident.resolved_at && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Resolved At</span>
                    <span className="text-slate-300">{formatDate(selectedIncident.resolved_at)}</span>
                  </div>
                )}
                {selectedIncident.resolution_note && (
                  <div>
                    <span className="block text-slate-500 mb-1">Resolution</span>
                    <p className="rounded bg-slate-800 p-2 text-slate-300">{selectedIncident.resolution_note}</p>
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
