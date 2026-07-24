"use client";

import React from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import {
  Link2, BarChart, Server, AlertTriangle,
  ShieldCheck, PlayCircle, ArrowRight,
} from "lucide-react";

// Index only — the previous page rendered each report's JSON via
// `JSON.stringify(v).slice(0,80)` which was both lossy and a duplicate of the
// dedicated pages already in the sidebar. This version routes users straight
// to the richer dedicated page for each concern.
const REPORT_LINKS: Array<{
  key: string;
  label: string;
  url: string;
  description: string;
  icon: React.ReactNode;
}> = [
  {
    key: "market_matching",
    label: "Market Matching",
    url: "/matching",
    description: "Tracked matches with/without a betting market, confidence breakdown, and the unset unmatched queue.",
    icon: <Link2 className="h-5 w-5" />,
  },
  {
    key: "odds_coverage",
    label: "Odds Coverage",
    url: "/matches",
    description: "Per-match odds tick counts and coverage ratios across finished matches.",
    icon: <BarChart className="h-5 w-5" />,
  },
  {
    key: "collection",
    label: "Collection",
    url: "/collectors",
    description: "Per-collector health, record counts, heartbeat, and recent polling activity.",
    icon: <Server className="h-5 w-5" />,
  },
  {
    key: "failure_distribution",
    label: "Failure Distribution",
    url: "/quality",
    description: "Failure-category breakdown across completed matches — which quality gates most matches fall at.",
    icon: <AlertTriangle className="h-5 w-5" />,
  },
  {
    key: "dataset_quality",
    label: "Dataset Quality",
    url: "/quality",
    description: "Quality grade distribution A–F across the finalized match dataset.",
    icon: <ShieldCheck className="h-5 w-5" />,
  },
  {
    key: "replay_readiness",
    label: "Replay Readiness",
    url: "/validation",
    description: "Validation pass rate, replay/backtest readiness flags, and completeness percentages.",
    icon: <PlayCircle className="h-5 w-5" />,
  },
];

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Reports</h1>
      <p className="text-sm text-slate-500">
        Each report below opens its dedicated page with filtering, sorting, and drill-down —
        replacing the previous flat JSON summary cards.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {REPORT_LINKS.map((r) => (
          <Link key={r.key} href={r.url} className="block">
            <Card className="cursor-pointer transition-colors hover:border-slate-700 hover:bg-slate-800/40 h-full">
              <CardContent className="flex h-full items-start gap-3 p-4">
                <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-emerald-600/10 text-emerald-400">
                  {r.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-200">{r.label}</span>
                    <Badge variant="outline" className="text-xs">{r.key}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{r.description}</p>
                </div>
                <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-slate-500" />
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
