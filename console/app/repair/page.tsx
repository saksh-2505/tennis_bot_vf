"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type RepairSummary } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Wrench, CheckCircle } from "lucide-react";

export default function RepairPage() {
  const { data, isLoading, error } = useQuery<RepairSummary>({
    queryKey: ["repairsSummary"],
    queryFn: () => api.repairsSummary(),
  });

  const s = data;
  const actions = s?.by_repair_action ?? [];

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
          <div className="grid grid-cols-2 gap-4">
            <StatCard title="Total Repaired" value={s.total_repaired} icon={<Wrench className="h-4 w-4" />} />
            <StatCard
              title="Repair Actions"
              value={actions.length}
              color="#22c55e"
              icon={<CheckCircle className="h-4 w-4 text-emerald-400" />}
            />
          </div>

          {actions.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">By Repair Action</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {actions.map(({ action, count }) => (
                    <div key={action} className="flex items-center justify-between rounded border border-slate-800 p-3">
                      <span className="text-sm text-slate-300">{action}</span>
                      <Badge variant="outline">{count} matches</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
