"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type QualityDistribution, type QualityFailures } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/Tabs";
import { ShieldCheck } from "lucide-react";

const gradeColors: Record<string, string> = {
  A: "bg-emerald-500", B: "bg-blue-500", C: "bg-yellow-500",
  D: "bg-orange-500", F: "bg-red-500",
};

export default function QualityPage() {
  const dist = useQuery<QualityDistribution>({
    queryKey: ["qualityDistribution"],
    queryFn: () => api.qualityDistribution(),
  });

  const failures = useQuery<QualityFailures>({
    queryKey: ["qualityFailures"],
    queryFn: () => api.qualityFailures(),
  });

  const distribution = dist.data?.distribution ?? [];
  const maxCount = Math.max(...distribution.map((d) => d.count), 1);
  const totalGraded = dist.data?.total_matches ?? 0;
  const failureCategories = failures.data?.by_category ?? {};

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Dataset Quality</h1>

      <div className="grid grid-cols-3 gap-4">
        <StatCard
          title="Total Graded"
          value={dist.isLoading ? "—" : totalGraded}
          icon={<ShieldCheck className="h-4 w-4" />}
        />
        <StatCard
          title="Avg Quality Score"
          value={dist.isLoading ? "—" : dist.data?.avg_quality_score?.toFixed(1) ?? "—"}
        />
        <StatCard
          title="Total Failures"
          value={failures.isLoading ? "—" : failures.data?.total_failures ?? "—"}
          color={failures.data && failures.data.total_failures > 0 ? "#ef4444" : "#22c55e"}
        />
      </div>

      <Tabs defaultValue="distribution">
        <TabsList>
          <TabsTrigger value="distribution">Grade Distribution</TabsTrigger>
          <TabsTrigger value="failures">Failure Categories</TabsTrigger>
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
                <p className="text-sm text-slate-500">No quality data</p>
              ) : (
                <div className="space-y-3">
                  {distribution.map((d) => (
                    <div key={d.grade} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">Grade {d.grade}</span>
                        <span className="text-slate-500">{d.percentage}% ({d.count})</span>
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
                <div className="grid grid-cols-5 gap-2 text-center text-sm">
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
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Failure Categories</CardTitle>
            </CardHeader>
            <CardContent>
              {failures.isLoading ? (
                <p className="text-sm text-slate-500">Loading...</p>
              ) : Object.keys(failureCategories).length === 0 ? (
                <p className="text-sm text-slate-500">No failures</p>
              ) : (
                <div className="space-y-2">
                  {Object.entries(failureCategories).map(([cat, count]) => (
                    <div key={cat} className="flex items-center justify-between rounded border border-slate-800 p-3">
                      <span className="text-sm text-slate-300">{cat}</span>
                      <Badge variant="destructive">{count}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
