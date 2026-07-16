"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { FileText } from "lucide-react";

const reportLabels: Record<string, string> = {
  market_matching: "Market Matching",
  odds_coverage: "Odds Coverage",
  collection: "Collection",
  failure_distribution: "Failure Distribution",
  dataset_quality: "Dataset Quality",
  replay_readiness: "Replay Readiness",
};

export default function ReportsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["reports"],
    queryFn: () => api.reports(),
  });

  const reports = (data ?? {}) as Record<string, any>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Reports</h1>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading reports</p>
      ) : Object.keys(reports).length === 0 ? (
        <p className="text-sm text-slate-500">No reports generated yet</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(reportLabels).map(([key, label]) => {
            const report = reports[key] as any;
            if (!report) return null;
            return (
              <Card key={key}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <FileText className="h-4 w-4" />
                    {label}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-1 text-xs text-slate-400">
                    {Object.entries(report).map(([k, v]) => {
                      if (k === "generated_at" || k === "ready_matches" || k === "by_tournament") return null;
                      let display = "";
                      if (typeof v === "number") display = v.toFixed(v === Math.round(v) ? 0 : 2);
                      else if (typeof v === "object") display = JSON.stringify(v).slice(0, 80);
                      else display = String(v);
                      return (
                        <div key={k} className="flex justify-between">
                          <span>{k}</span>
                          <span className="text-slate-200">{display}</span>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
