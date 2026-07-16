"use client";

import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api, type TimelineEntry } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Select } from "@/components/ui/Select";
import { Input } from "@/components/ui/Input";
import { formatDate } from "@/lib/utils";
import { Clock, ExternalLink, Filter } from "lucide-react";

const severityBadge = (sev: string) => {
  if (sev === "CRITICAL" || sev === "ERROR") return <Badge variant="destructive">{sev}</Badge>;
  if (sev === "WARNING") return <Badge variant="warning">{sev}</Badge>;
  return <Badge variant="outline">{sev}</Badge>;
};

export default function TimelinePage() {
  const router = useRouter();
  const [severityFilter, setSeverityFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["timeline"],
    queryFn: () => api.timeline(),
  });

  const entries = data?.items ?? [];

  const filtered = useMemo(() => {
    return entries.filter((e: any) => {
      if (severityFilter && e.level !== severityFilter) return false;
      if (sourceFilter && !e.source.toLowerCase().includes(sourceFilter.toLowerCase())) return false;
      return true;
    });
  }, [entries, severityFilter, sourceFilter]);

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

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Clock className="h-6 w-6 text-slate-400" />
        <h1 className="text-2xl font-bold text-slate-100">Timeline</h1>
      </div>

      <div className="flex items-end gap-3">
        <div className="w-40">
          <label className="mb-1 block text-xs text-slate-400">Severity</label>
          <Select options={severityOptions} value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} />
        </div>
        <div className="w-48">
          <label className="mb-1 block text-xs text-slate-400">Source</label>
          <Select options={sources} value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)} />
        </div>
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading timeline</p>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-slate-500">No timeline entries</p>
      ) : (
        <div className="relative space-y-0">
          <div className="absolute left-[13px] top-0 h-full w-0.5 bg-slate-800" />

          {filtered.map((entry, i) => (
            <div key={i} className="relative flex gap-4 pb-4">
              <div className="relative z-10 mt-1.5 h-3 w-3 shrink-0 rounded-full border-2 border-slate-800 bg-slate-700" />

              <div className="min-w-0 flex-1 rounded-lg border border-slate-800 bg-slate-900 p-3">
                <div className="mb-2 flex items-center gap-2">
                  <span className="text-xs text-slate-500">{formatDate(entry.timestamp)}</span>
                  <Badge variant="outline" className="text-xs">{entry.source}</Badge>
                  {severityBadge(entry.level)}
                  {entry.tracked_match_id && (
                    <button
                      onClick={() => router.push(`/matches/${entry.tracked_match_id}`)}
                      className="ml-auto flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300"
                    >
                      <ExternalLink className="h-3 w-3" /> Match #{entry.tracked_match_id}
                    </button>
                  )}
                </div>
                <p className="text-sm text-slate-300">{entry.message}</p>
                {entry.event_id && (
                  <p className="mt-1 text-xs text-slate-600">Event: {entry.event_id}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
