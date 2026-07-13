"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type ValidationSummary } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { CheckCircle, XCircle, ShieldCheck, Target } from "lucide-react";
import { formatPct } from "@/lib/utils";

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
          title="Total Checks"
          value={isLoading ? "—" : s?.total_checks ?? "—"}
          icon={<Target className="h-4 w-4" />}
        />
        <StatCard
          title="Passed"
          value={isLoading ? "—" : s?.passed ?? "—"}
          icon={<CheckCircle className="h-4 w-4 text-emerald-400" />}
          color="#22c55e"
        />
        <StatCard
          title="Failed"
          value={isLoading ? "—" : s?.failed ?? "—"}
          icon={<XCircle className="h-4 w-4 text-red-400" />}
          color={s && s.failed > 0 ? "#ef4444" : "#22c55e"}
        />
        <StatCard
          title="Pass Rate"
          value={isLoading ? "—" : formatPct(s?.pass_rate ?? null)}
          color={s && s.pass_rate >= 90 ? "#22c55e" : s && s.pass_rate >= 70 ? "#f59e0b" : "#ef4444"}
        />
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading validation data</p>
      ) : !s ? (
        <p className="text-sm text-slate-500">No validation data</p>
      ) : (
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
                  style={{ width: `${s.pass_rate}%` }}
                >
                  {s.pass_rate.toFixed(0)}%
                </div>
                <div
                  className="flex items-center justify-center bg-red-600 text-xs font-bold text-white transition-all"
                  style={{ width: `${100 - s.pass_rate}%` }}
                >
                  {(100 - s.pass_rate).toFixed(0)}%
                </div>
              </div>
              <div className="mt-3 flex justify-between text-xs text-slate-500">
                <span>Passed: {s.passed}</span>
                <span>Failed: {s.failed}</span>
              </div>
            </div>
          </div>

          {Object.keys(s.by_check_type).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">By Check Type</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(s.by_check_type).map(([type, counts]) => {
                    const total = counts.passed + counts.failed;
                    const pct = total > 0 ? (counts.passed / total) * 100 : 0;
                    return (
                      <div key={type} className="rounded border border-slate-800 p-3">
                        <div className="mb-1 flex items-center justify-between text-sm">
                          <span className="text-slate-300">{type}</span>
                          <span className="text-xs text-slate-500">{total} checks</span>
                        </div>
                        <div className="flex h-3 w-full overflow-hidden rounded bg-slate-800">
                          <div
                            className="bg-emerald-500 transition-all"
                            style={{ width: `${pct}%` }}
                          />
                          <div
                            className="bg-red-500 transition-all"
                            style={{ width: `${100 - pct}%` }}
                          />
                        </div>
                        <div className="mt-1 flex justify-between text-xs text-slate-500">
                          <span className="text-emerald-400">{counts.passed} passed</span>
                          <span className="text-red-400">{counts.failed} failed</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
