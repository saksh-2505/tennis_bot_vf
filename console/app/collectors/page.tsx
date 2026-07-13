"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type CollectorStatus } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";
import { Server, Activity, Clock, Database, AlertTriangle } from "lucide-react";

export default function CollectorsPage() {
  const { data, isLoading, error } = useQuery<CollectorStatus[]>({
    queryKey: ["collectors"],
    queryFn: () => api.collectors(),
    refetchInterval: 10000,
  });

  const collectors = data ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Collectors</h1>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading collectors</p>
      ) : collectors.length === 0 ? (
        <p className="text-sm text-slate-500">No collectors found</p>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {collectors.map((c) => (
            <Card key={c.name}>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-medium">{c.name}</CardTitle>
                <Badge variant={c.running ? "success" : "destructive"}>
                  {c.running ? "Active" : "Stopped"}
                </Badge>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="flex items-center gap-2">
                    <Server className="h-3 w-3 text-slate-500" />
                    <span className="text-xs text-slate-500">Type</span>
                    <span className="text-slate-300">{c.type}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Activity className="h-3 w-3 text-slate-500" />
                    <span className="text-xs text-slate-500">Status</span>
                    <span className="text-slate-300">{c.status}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="h-3 w-3 text-slate-500" />
                    <span className="text-xs text-slate-500">Last Run</span>
                    <span className="text-slate-300">{formatDate(c.last_run)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Database className="h-3 w-3 text-slate-500" />
                    <span className="text-xs text-slate-500">Collected</span>
                    <span className="text-slate-300">{c.matches_collected}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-3 w-3 text-slate-500" />
                    <span className="text-xs text-slate-500">Errors</span>
                    <span className={c.errors > 0 ? "text-red-400" : "text-slate-300"}>{c.errors}</span>
                  </div>
                  {c.avg_latency != null && (
                    <div className="flex items-center gap-2">
                      <Clock className="h-3 w-3 text-slate-500" />
                      <span className="text-xs text-slate-500">Avg Latency</span>
                      <span className="text-slate-300">{c.avg_latency.toFixed(1)} ms</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
