"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type PipelineStatus } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";
import { GitBranch, CheckCircle, AlertTriangle, XCircle, Clock } from "lucide-react";

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

export default function PipelinePage() {
  const { data, isLoading, error } = useQuery<PipelineStatus>({
    queryKey: ["pipelineStatus"],
    queryFn: () => api.pipelineStatus(),
    refetchInterval: 30_000,
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
          {stages.map((stage, i) => (
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

              <Card className="flex-1">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium">{stage.name}</CardTitle>
                  {statusBadge(stage.status)}
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
          ))}
        </div>
      )}
    </div>
  );
}
