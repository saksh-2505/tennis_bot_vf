"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type VerificationHealthPoint } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { FileCheck, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { formatDate } from "@/lib/utils";

export default function VerificationPage() {
  const { data, isLoading, error } = useQuery<VerificationHealthPoint[]>({
    queryKey: ["verificationHistory"],
    queryFn: () => api.verificationHistory(),
  });

  const history = data ?? [];
  const latest = history[history.length - 1];
  const previous = history[history.length - 2];

  const trend =
    latest && previous
      ? latest.health_score > previous.health_score
        ? "up"
        : latest.health_score < previous.health_score
          ? "down"
          : "neutral"
      : undefined;

  const maxScore = Math.max(100, ...history.map((h) => h.health_score));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Verification</h1>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading verification data</p>
      ) : !latest ? (
        <p className="text-sm text-slate-500">No verification history</p>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4">
            <StatCard
              title="Health Score"
              value={`${latest.health_score.toFixed(1)}%`}
              icon={<FileCheck className="h-4 w-4" />}
              color={
                latest.health_score >= 90
                  ? "#22c55e"
                  : latest.health_score >= 70
                    ? "#f59e0b"
                    : "#ef4444"
              }
              trend={trend}
            />
            <StatCard
              title="Checks Passed"
              value={latest.checks_passed}
              icon={<TrendingUp className="h-4 w-4 text-emerald-400" />}
            />
            <StatCard
              title="Checks Total"
              value={latest.checks_total}
              icon={<Minus className="h-4 w-4" />}
            />
          </div>

          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-400">Trend:</span>
            {trend === "up" ? (
              <Badge variant="success" className="flex items-center gap-1">
                <TrendingUp className="h-3 w-3" /> Improving
              </Badge>
            ) : trend === "down" ? (
              <Badge variant="destructive" className="flex items-center gap-1">
                <TrendingDown className="h-3 w-3" /> Declining
              </Badge>
            ) : (
              <Badge variant="outline" className="flex items-center gap-1">
                <Minus className="h-3 w-3" /> Stable
              </Badge>
            )}
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Health Score History ({history.length} points)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-1">
                {history.slice(-30).map((point, i) => (
                  <div key={i} className="flex items-center gap-3 text-xs">
                    <span className="w-36 text-slate-500">{formatDate(point.timestamp)}</span>
                    <div className="flex-1">
                      <div className="h-4 w-full overflow-hidden rounded bg-slate-800">
                        <div
                          className={`h-full rounded transition-all ${
                            point.health_score >= 90
                              ? "bg-emerald-500"
                              : point.health_score >= 70
                                ? "bg-yellow-500"
                                : "bg-red-500"
                          }`}
                          style={{ width: `${(point.health_score / maxScore) * 100}%` }}
                        />
                      </div>
                    </div>
                    <span className="w-16 text-right font-mono text-slate-300">
                      {point.health_score.toFixed(1)}%
                    </span>
                    <span className="w-20 text-right text-slate-500">
                      {point.checks_passed}/{point.checks_total}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
