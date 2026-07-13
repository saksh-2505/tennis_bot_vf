"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type ObservabilityHealth } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Eye, Activity, CheckCircle, XCircle, AlertTriangle } from "lucide-react";

const statusIcon: Record<string, React.ReactNode> = {
  healthy: <CheckCircle className="h-4 w-4 text-emerald-400" />,
  degraded: <AlertTriangle className="h-4 w-4 text-yellow-400" />,
  failed: <XCircle className="h-4 w-4 text-red-400" />,
  disconnected: <XCircle className="h-4 w-4 text-red-400" />,
  connected: <CheckCircle className="h-4 w-4 text-emerald-400" />,
};

export default function ObservabilityPage() {
  const { data, isLoading, error } = useQuery<ObservabilityHealth>({
    queryKey: ["observabilityHealth"],
    queryFn: () => api.observabilityHealth(),
  });

  const h = data;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Observability</h1>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading health data</p>
      ) : !h ? (
        <p className="text-sm text-slate-500">No health data</p>
      ) : (
        <>
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-400">Overall Status:</span>
            {h.overall_status === "healthy" ? (
              <Badge variant="success">Healthy</Badge>
            ) : h.overall_status === "degraded" ? (
              <Badge variant="warning">Degraded</Badge>
            ) : (
              <Badge variant="destructive">Unhealthy</Badge>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            {h.components.map((comp) => (
              <Card key={comp.name}>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-sm font-medium">{comp.name}</CardTitle>
                  {statusIcon[comp.status] ?? (
                    <Activity className="h-4 w-4 text-slate-500" />
                  )}
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-500">Status</span>
                      {comp.status === "healthy" || comp.status === "connected" ? (
                        <Badge variant="success">{comp.status}</Badge>
                      ) : comp.status === "degraded" ? (
                        <Badge variant="warning">{comp.status}</Badge>
                      ) : (
                        <Badge variant="destructive">{comp.status}</Badge>
                      )}
                    </div>
                    {comp.latency_ms != null && (
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-500">Latency</span>
                        <span className="text-slate-300">{comp.latency_ms.toFixed(1)} ms</span>
                      </div>
                    )}
                    {comp.message && (
                      <div className="rounded bg-slate-800 p-2 text-xs text-slate-400">
                        {comp.message}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Component Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-3 text-center text-sm">
                <div className="rounded border border-slate-800 p-3">
                  <div className="text-2xl font-bold text-emerald-400">
                    {h.components.filter((c) => c.status === "healthy" || c.status === "connected").length}
                  </div>
                  <div className="text-xs text-slate-500">Healthy</div>
                </div>
                <div className="rounded border border-slate-800 p-3">
                  <div className="text-2xl font-bold text-yellow-400">
                    {h.components.filter((c) => c.status === "degraded").length}
                  </div>
                  <div className="text-xs text-slate-500">Degraded</div>
                </div>
                <div className="rounded border border-slate-800 p-3">
                  <div className="text-2xl font-bold text-red-400">
                    {h.components.filter((c) => c.status === "failed" || c.status === "disconnected").length}
                  </div>
                  <div className="text-xs text-slate-500">Failed</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
