"use client";

import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api, type TimelineEntry } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Select } from "@/components/ui/Select";
import { Input } from "@/components/ui/Input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { formatDate } from "@/lib/utils";
import { ScrollText, ExternalLink, Search, Filter } from "lucide-react";

const severityBadge = (sev: string) => {
  if (sev === "CRITICAL" || sev === "ERROR") return <Badge variant="destructive">{sev}</Badge>;
  if (sev === "WARNING") return <Badge variant="warning">{sev}</Badge>;
  return <Badge variant="outline">{sev}</Badge>;
};

export default function LogsPage() {
  const router = useRouter();
  const [severity, setSeverity] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [textSearch, setTextSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["timeline"],
    queryFn: () => api.timeline(),
  });

  const entries = data?.items ?? [];

  const sources = useMemo(() => {
    const set = new Set(entries.map((e) => e.source));
    return [{ label: "All", value: "" }, ...Array.from(set).map((s) => ({ label: s, value: s }))];
  }, [entries]);

  const severityOptions = [
    { label: "All", value: "" },
    { label: "INFO", value: "INFO" },
    { label: "WARNING", value: "WARNING" },
    { label: "ERROR", value: "ERROR" },
    { label: "CRITICAL", value: "CRITICAL" },
  ];

  const filtered = useMemo(() => {
    return entries.filter((e) => {
      if (severity && e.level !== severity) return false;
      if (sourceFilter && !e.source.toLowerCase().includes(sourceFilter.toLowerCase())) return false;
      if (textSearch) {
        const q = textSearch.toLowerCase();
        if (!e.message.toLowerCase().includes(q) && !e.source.toLowerCase().includes(q)) return false;
      }
      const ts = e.timestamp || "";
      if (dateFrom && ts < dateFrom) return false;
      if (dateTo && ts > dateTo + "T23:59:59") return false;
      return true;
    });
  }, [entries, severity, sourceFilter, textSearch, dateFrom, dateTo]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ScrollText className="h-6 w-6 text-slate-400" />
        <h1 className="text-2xl font-bold text-slate-100">System Logs</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Filter className="h-4 w-4" /> Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-5 gap-3">
            <div>
              <label className="mb-1 block text-xs text-slate-400">Search text</label>
              <Input
                placeholder="Search in description..."
                value={textSearch}
                onChange={(e) => setTextSearch(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">Severity</label>
              <Select options={severityOptions} value={severity} onChange={(e) => setSeverity(e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">Source</label>
              <Select options={sources} value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">From Date</label>
              <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">To Date</label>
              <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            </div>
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading logs</p>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-slate-500">No log entries match the filters</p>
      ) : (
        <div className="space-y-1">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs text-slate-500">
              Showing {filtered.length} of {entries.length} entries
            </span>
          </div>

          {filtered.slice(0, 200).map((entry, i) => (
            <div
              key={i}
              className={`flex items-start gap-3 rounded border p-3 text-sm ${
                entry.level === "CRITICAL" || entry.level === "ERROR"
                  ? "border-red-500/30 bg-red-500/5"
                  : entry.level === "WARNING"
                    ? "border-yellow-500/30 bg-yellow-500/5"
                    : "border-slate-800 bg-slate-900"
              }`}
            >
              <div className="flex shrink-0 flex-col items-end">
                <span className="whitespace-nowrap font-mono text-xs text-slate-500">
                  {formatDate(entry.timestamp)}
                </span>
                <Badge variant="outline" className="mt-1 text-xs">{entry.source}</Badge>
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  {severityBadge(entry.level)}
                  {entry.tracked_match_id && (
                    <button
                      onClick={() => router.push(`/matches/${entry.tracked_match_id}`)}
                      className="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300"
                    >
                      <ExternalLink className="h-3 w-3" /> Match #{entry.tracked_match_id}
                    </button>
                  )}
                </div>
                <p className="mt-1 text-slate-300">{entry.message}</p>
                {entry.event_id && (
                  <p className="mt-0.5 text-xs text-slate-600">Event ID: {entry.event_id}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
