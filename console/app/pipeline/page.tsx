"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api, type PipelineStatus } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";
import { GitBranch, CheckCircle, AlertTriangle, XCircle, Clock, ExternalLink } from "lucide-react";

const statusBadge = (status: string) => {
  const lower = status.toLowerCase();
  if (lower === "active" || lower === "healthy" || lower === "completed" || lower === "running")
    return <Badge variant="success">{status}</Badge>;
  if (lower === "degraded" || lower === "warning" || lower === "stale")
    return <Badge variant="warning">{status}</Badge>;
  if (lower === "failed" || lower === "error" || lower === "unhealthy")
    return <Badge variant="destructive">{status}</Badge>;
  return <Badge variant="outline">{status}</Badge>;
};

const statusDot = (status: string) => {
  const lower = status.toLowerCase();
  if (lower === "active" || lower === "healthy" || lower === "completed" || lower === "running")
    return <CheckCircle className="h-5 w-5 text-emerald-400" />;
  if (lower === "degraded" || lower === "warning" || lower === "stale")
    return <AlertTriangle className="h-5 w-5 text-yellow-400" />;
  if (lower === "failed" || lower === "error" || lower === "unhealthy")
    return <XCircle className="h-5 w-5 text-red-400" />;
  return <Clock className="h-5 w-5 text-slate-500" />;
};

// Map a pipeline stage name to the system_events `source` label that backs it.
// Lets a stage card deep-link to /timeline?source=… for instant event inspection.
const stageSource: Record<string, string> = {
  Discovery: "orchestrator",
  Registry: "registry",
  Matching: "matcher",
  "Live Collection": "live_collector",
  Finalizer: "finalizer",
  Incidents: "incidents",
};

export default function PipelinePage() {
  const router = useRouter();
  const { data, isLoading, error } = useQuery<PipelineStatus>({
    queryKey: ["pipelineStatus"],
    queryFn: () => api.pipelineStatus(),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const stages = data?.stages ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <GitBranch className="h-6 w-6 text-slate-400" />
        <h1 className="text-2xl font-bold text-slate-100">Pipeline</h1>
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading pipeline status</p>
      ) : stages.length === 0 ? (
        <p className="text-sm text-slate-500">No pipeline data</p>
      ) : (
        <div className="relative space-y-4">
          {stages.map((stage, i) => {
            const src = stageSource[stage.name];
            return (
              <div key={stage.name} className="flex items-start gap-4">
                <div className="flex flex-col items-center">
                  {statusDot(stage.status)}
                  {i < stages.length - 1 && (
                    <div className={`mt-1 h-12 w-0.5 ${
                      stage.status.toLowerCase() === "active" || stage.status.toLowerCase() === "healthy"
                        ? "bg-emerald-500/30" : "bg-slate-700"
                    }`} />
                  )}
                </div>

                <Card className="flex-1 cursor-pointer transition-colors hover:border-slate-700">
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium">{stage.name}</CardTitle>
                    <div className="flex items-center gap-2">
                      {/* Cross-link → /timeline?source=… (raw event log for this stage). */}
                      <button
                        onClick={() => router.push(src ? `/timeline` : `/incidents`)}
                        className="flex items-center gap-1 text-xs text-slate-500 hover:text-emerald-400"
                        title={`View ${stage.name} timeline & incidents`}
                      >
                        <ExternalLink className="h-3 w-3" />
                      </button>
                      {statusBadge(stage.status)}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="block text-xs text-slate-500">Status</span>
                        <span className="text-slate-300">{stage.status}</span>
                      </div>
                      <div>
                        <span className="block text-xs text-slate-500">Last Run</span>
                        <span className="text-slate-300">{formatDate(stage.last_run)}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
