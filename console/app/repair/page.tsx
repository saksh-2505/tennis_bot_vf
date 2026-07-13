"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type RepairSummary } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Wrench, Clock, CheckCircle, Activity, Loader } from "lucide-react";

export default function RepairPage() {
  const { data, isLoading, error } = useQuery<RepairSummary>({
    queryKey: ["repairsSummary"],
    queryFn: () => api.repairsSummary(),
  });

  const s = data;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Wrench className="h-6 w-6 text-slate-400" />
        <h1 className="text-2xl font-bold text-slate-100">Repair</h1>
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading repair data</p>
      ) : !s ? (
        <p className="text-sm text-slate-500">No repair data</p>
      ) : (
        <>
          <div className="grid grid-cols-5 gap-4">
            <StatCard title="Total Repairs" value={s.total_repairs} icon={<Wrench className="h-4 w-4" />} />
            <StatCard
              title="Pending"
              value={s.pending}
              color={s.pending > 0 ? "#f59e0b" : undefined}
              icon={<Clock className="h-4 w-4 text-yellow-400" />}
            />
            <StatCard
              title="In Progress"
              value={s.in_progress}
              color={s.in_progress > 0 ? "#3b82f6" : undefined}
              icon={<Loader className="h-4 w-4 text-blue-400" />}
            />
            <StatCard
              title="Completed"
              value={s.completed}
              color="#22c55e"
              icon={<CheckCircle className="h-4 w-4 text-emerald-400" />}
            />
            <StatCard
              title="Failed"
              value={s.failed}
              color={s.failed > 0 ? "#ef4444" : undefined}
              icon={<Activity className="h-4 w-4 text-red-400" />}
            />
          </div>

          <div className="grid grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Repair Status Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex h-6 w-full overflow-hidden rounded bg-slate-800">
                  {s.pending > 0 && (
                    <div
                      className="flex items-center justify-center bg-yellow-600 text-xs font-bold text-white"
                      style={{ width: `${(s.pending / Math.max(s.total_repairs, 1)) * 100}%` }}
                    >
                      {s.pending}
                    </div>
                  )}
                  {s.in_progress > 0 && (
                    <div
                      className="flex items-center justify-center bg-blue-600 text-xs font-bold text-white"
                      style={{ width: `${(s.in_progress / Math.max(s.total_repairs, 1)) * 100}%` }}
                    >
                      {s.in_progress}
                    </div>
                  )}
                  {s.completed > 0 && (
                    <div
                      className="flex items-center justify-center bg-emerald-600 text-xs font-bold text-white"
                      style={{ width: `${(s.completed / Math.max(s.total_repairs, 1)) * 100}%` }}
                    >
                      {s.completed}
                    </div>
                  )}
                  {s.failed > 0 && (
                    <div
                      className="flex items-center justify-center bg-red-600 text-xs font-bold text-white"
                      style={{ width: `${(s.failed / Math.max(s.total_repairs, 1)) * 100}%` }}
                    >
                      {s.failed}
                    </div>
                  )}
                </div>
                <div className="mt-3 flex justify-between text-xs text-slate-500">
                  <span className="flex items-center gap-1">
                    <span className="inline-block h-2 w-2 rounded-full bg-yellow-500" /> Pending
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="inline-block h-2 w-2 rounded-full bg-blue-500" /> In Progress
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" /> Completed
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="inline-block h-2 w-2 rounded-full bg-red-500" /> Failed
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">By Repair Type</CardTitle>
              </CardHeader>
              <CardContent>
                {Object.keys(s.by_type).length === 0 ? (
                  <p className="text-sm text-slate-500">No breakdown available</p>
                ) : (
                  <div className="space-y-2">
                    {Object.entries(s.by_type).map(([type, count]) => (
                      <div key={type} className="flex items-center justify-between rounded border border-slate-800 p-2">
                        <span className="text-sm text-slate-300">{type}</span>
                        <Badge variant="outline">{count}</Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
