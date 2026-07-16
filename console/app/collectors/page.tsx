"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type CollectorStatus } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";
import { Server, Clock, Database } from "lucide-react";

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
                <Badge variant={c.status === "active" ? "success" : "destructive"}>
                  {c.status}
                </Badge>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="flex items-center gap-2">
                    <Database className="h-3 w-3 text-slate-500" />
                    <span className="text-xs text-slate-500">Records</span>
                    <span className="text-slate-300">{c.records_count.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="h-3 w-3 text-slate-500" />
                    <span className="text-xs text-slate-500">Last Poll</span>
                    <span className="text-slate-300">{formatDate(c.last_poll)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Server className="h-3 w-3 text-slate-500" />
                    <span className="text-xs text-slate-500">Heartbeat</span>
                    <span className={c.heartbeat_seconds_ago != null && c.heartbeat_seconds_ago > 600 ? "text-red-400" : "text-slate-300"}>
                      {c.heartbeat_seconds_ago != null ? `${c.heartbeat_seconds_ago}s ago` : "N/A"}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
