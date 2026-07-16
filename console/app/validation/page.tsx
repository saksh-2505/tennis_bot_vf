"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type ValidationSummary } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { CheckCircle, XCircle, ShieldCheck, Target } from "lucide-react";

export default function ValidationPage() {
  const { data, isLoading, error } = useQuery<ValidationSummary>({
    queryKey: ["validationSummary"],
    queryFn: () => api.validationSummary(),
  });

  const s = data;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Validation</h1>

      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Total Completed"
          value={isLoading ? "—" : s?.total_completed ?? "—"}
          icon={<Target className="h-4 w-4" />}
        />
        <StatCard
          title="Validation Passed"
          value={isLoading ? "—" : s?.validation_passed ?? "—"}
          icon={<CheckCircle className="h-4 w-4 text-emerald-400" />}
          color="#22c55e"
        />
        <StatCard
          title="Validation Failed"
          value={isLoading ? "—" : s?.validation_failed ?? "—"}
          icon={<XCircle className="h-4 w-4 text-red-400" />}
          color={s && s.validation_failed > 0 ? "#ef4444" : "#22c55e"}
        />
        <StatCard
          title="Pass Rate"
          value={isLoading ? "—" : s ? `${s.validation_pass_pct}%` : "—"}
          color={s && s.validation_pass_pct >= 90 ? "#22c55e" : s && s.validation_pass_pct >= 70 ? "#f59e0b" : "#ef4444"}
        />
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading validation data</p>
      ) : s ? (
        <div className="space-y-4">
          <div className="flex gap-4">
            <div className="flex-1 rounded-lg border border-slate-800 bg-slate-900 p-6">
              <div className="mb-4 flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-emerald-400" />
                <h3 className="text-sm font-medium text-slate-300">Pass/Fail Breakdown</h3>
              </div>
              <div className="flex h-8 w-full overflow-hidden rounded bg-slate-800">
                <div
                  className="flex items-center justify-center bg-emerald-600 text-xs font-bold text-white transition-all"
                  style={{ width: `${s.validation_pass_pct}%` }}
                >
                  {s.validation_pass_pct}%
                </div>
                <div
                  className="flex items-center justify-center bg-red-600 text-xs font-bold text-white transition-all"
                  style={{ width: `${100 - s.validation_pass_pct}%` }}
                >
                  {(100 - s.validation_pass_pct).toFixed(0)}%
                </div>
              </div>
              <div className="mt-3 flex justify-between text-xs text-slate-500">
                <span>Passed: {s.validation_passed}</span>
                <span>Failed: {s.validation_failed}</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Ready for Replay</CardTitle>
              </CardHeader>
              <CardContent>
                <span className="text-2xl font-bold text-slate-100">{s.ready_for_replay}</span>
                <span className="ml-2 text-sm text-slate-500">
                  ({(s.ready_for_replay / Math.max(s.total_completed, 1) * 100).toFixed(1)}%)
                </span>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Ready for Backtesting</CardTitle>
              </CardHeader>
              <CardContent>
                <span className="text-2xl font-bold text-slate-100">{s.ready_for_backtesting}</span>
                <span className="ml-2 text-sm text-slate-500">
                  ({(s.ready_for_backtesting / Math.max(s.total_completed, 1) * 100).toFixed(1)}%)
                </span>
              </CardContent>
            </Card>
          </div>
        </div>
      ) : (
        <p className="text-sm text-slate-500">No validation data</p>
      )}
    </div>
  );
}
