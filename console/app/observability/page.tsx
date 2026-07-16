"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type ObservabilityHealth } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Database, Eye } from "lucide-react";

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
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <StatCard
              title="Database"
              value={h.db ? "Connected" : "Disconnected"}
              icon={<Database className="h-4 w-4" />}
              color={h.db ? "#22c55e" : "#ef4444"}
            />
            <StatCard
              title="API Version"
              value={h.version}
              icon={<Eye className="h-4 w-4" />}
            />
          </div>
        </div>
      )}
    </div>
  );
}
