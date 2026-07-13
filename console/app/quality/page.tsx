"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type QualityDistribution, type QualityFailure } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { DataTable } from "@/components/data/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/Tabs";
import { ShieldCheck } from "lucide-react";
import { formatDate } from "@/lib/utils";

const gradeColors: Record<string, string> = {
  A: "bg-emerald-500", B: "bg-blue-500", C: "bg-yellow-500",
  D: "bg-orange-500", F: "bg-red-500",
};

const gradeLabels: Record<string, string> = {
  A: "Grade A", B: "Grade B", C: "Grade C", D: "Grade D", F: "Grade F",
};

export default function QualityPage() {
  const dist = useQuery<QualityDistribution[]>({
    queryKey: ["qualityDistribution"],
    queryFn: () => api.qualityDistribution(),
  });

  const failures = useQuery<QualityFailure[]>({
    queryKey: ["qualityFailures"],
    queryFn: () => api.qualityFailures(),
  });

  const distribution = dist.data ?? [];
  const maxCount = Math.max(...distribution.map((d) => d.count), 1);

  const totalGraded = distribution.reduce((sum, d) => sum + d.count, 0);

  const failureCols = [
    { field: "id", headerName: "ID", width: 80 },
    { field: "event_id", headerName: "Event ID", flex: 1 },
    {
      field: "severity",
      headerName: "Severity",
      width: 100,
      cellRenderer: (p: any) => {
        const s = p.value;
        if (s === "CRITICAL" || s === "ERROR") return <Badge variant="destructive">{s}</Badge>;
        if (s === "WARNING") return <Badge variant="warning">{s}</Badge>;
        return <Badge variant="outline">{s}</Badge>;
      },
    },
    { field: "check_type", headerName: "Check Type", flex: 1 },
    { field: "field", headerName: "Field", flex: 1 },
    {
      field: "resolved",
      headerName: "Resolved",
      width: 100,
      cellRenderer: (p: any) =>
        p.value ? <Badge variant="success">Yes</Badge> : <Badge variant="destructive">No</Badge>,
    },
    { field: "timestamp", headerName: "Timestamp", valueFormatter: (p: any) => formatDate(p.value), flex: 1.5 },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Dataset Quality</h1>

      <div className="grid grid-cols-2 gap-4">
        <StatCard
          title="Total Graded"
          value={dist.isLoading ? "—" : totalGraded}
          icon={<ShieldCheck className="h-4 w-4" />}
        />
        <StatCard
          title="Failures"
          value={failures.isLoading ? "—" : failures.data?.length ?? "—"}
          color={failures.data && failures.data.length > 0 ? "#ef4444" : "#22c55e"}
        />
      </div>

      <Tabs defaultValue="distribution">
        <TabsList>
          <TabsTrigger value="distribution">Grade Distribution</TabsTrigger>
          <TabsTrigger value="failures">Failure Details</TabsTrigger>
        </TabsList>

        <TabsContent value="distribution">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Grade Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              {dist.isLoading ? (
                <p className="text-sm text-slate-500">Loading...</p>
              ) : distribution.length === 0 ? (
                <p className="text-sm text-slate-500">No quality distribution data</p>
              ) : (
                <div className="space-y-3">
                  {distribution.map((d) => (
                    <div key={d.grade} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">{gradeLabels[d.grade] ?? d.grade}</span>
                        <span className="text-slate-500">{d.percentage.toFixed(1)}% ({d.count})</span>
                      </div>
                      <div className="h-6 w-full overflow-hidden rounded bg-slate-800">
                        <div
                          className={`h-full rounded transition-all ${gradeColors[d.grade] || "bg-slate-600"}`}
                          style={{ width: `${(d.count / maxCount) * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {distribution.length > 0 && (
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="text-sm">Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-6 gap-2 text-center text-sm">
                  {distribution.map((d) => (
                    <div key={d.grade} className="rounded border border-slate-800 p-2">
                      <div className={`mb-1 mx-auto h-3 w-3 rounded-full ${gradeColors[d.grade] || "bg-slate-500"}`} />
                      <div className="font-bold text-slate-100">{d.grade}</div>
                      <div className="text-xs text-slate-500">{d.count}</div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="failures">
          {failures.isLoading ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : !failures.data || failures.data.length === 0 ? (
            <p className="text-sm text-slate-500">No quality failures</p>
          ) : (
            <DataTable rowData={failures.data} columnDefs={failureCols} height={600} />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
