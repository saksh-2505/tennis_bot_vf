"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type Report } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { StatCard } from "@/components/layout/StatCard";
import { formatDate } from "@/lib/utils";
import { FileText, Download, Clock, Database } from "lucide-react";

const reportIcons: Record<string, string> = {
  market_matching: "Market Matching",
  odds_coverage: "Odds Coverage",
  collection: "Collection",
  failure_distribution: "Failure Distribution",
  dataset_quality: "Dataset Quality",
  replay_readiness: "Replay Readiness",
};

export default function ReportsPage() {
  const { data, isLoading, error } = useQuery<Report[]>({
    queryKey: ["reports"],
    queryFn: () => api.reports(),
  });

  const reports = data ?? [];

  const totalSize = reports.reduce((sum, r) => sum + (r.size_bytes || 0), 0);
  const generatedCount = reports.filter((r) => r.status === "completed").length;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Reports</h1>

      <div className="grid grid-cols-4 gap-4">
        <StatCard title="Total Reports" value={reports.length} icon={<FileText className="h-4 w-4" />} />
        <StatCard
          title="Generated"
          value={isLoading ? "—" : generatedCount}
          icon={<Download className="h-4 w-4 text-emerald-400" />}
          color="#22c55e"
        />
        <StatCard
          title="Total Size"
          value={totalSize ? `${(totalSize / 1024).toFixed(1)} KB` : "—"}
          icon={<Database className="h-4 w-4" />}
        />
        <StatCard
          title="Pending"
          value={reports.filter((r) => r.status !== "completed").length}
          icon={<Clock className="h-4 w-4" />}
        />
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading reports</p>
      ) : reports.length === 0 ? (
        <p className="text-sm text-slate-500">No reports available</p>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {reports.map((report) => (
            <Card key={report.id}>
              <CardHeader className="flex flex-row items-start justify-between">
                <div>
                  <CardTitle className="text-sm">{report.title}</CardTitle>
                  <CardDescription className="text-xs">
                    {reportIcons[report.report_type] || report.report_type}
                  </CardDescription>
                </div>
                <Badge
                  variant={report.status === "completed" ? "success" : "warning"}
                >
                  {report.status}
                </Badge>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>{formatDate(report.generated_at)}</span>
                  <span>{report.format?.toUpperCase()}</span>
                  <span>{report.size_bytes ? `${(report.size_bytes / 1024).toFixed(1)} KB` : "—"}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
