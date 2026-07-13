"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type RegistrySummary, type MatchOverview } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { DataTable } from "@/components/data/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { BookOpen, Users } from "lucide-react";
import { useRouter } from "next/navigation";

const statusColors: Record<string, string> = {
  LIVE: "bg-emerald-500", FINISHED: "bg-slate-500",
  SCHEDULED: "bg-blue-500", DISCOVERED: "bg-yellow-500",
};

export default function RegistryPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");

  const summary = useQuery<RegistrySummary>({
    queryKey: ["registrySummary"],
    queryFn: () => api.registrySummary(),
  });

  const matches = useQuery<MatchOverview[]>({
    queryKey: ["searchMatches", search],
    queryFn: () => api.searchMatches(search ? { query: search } : {}),
  });

  const s = summary.data;
  const byType = s?.by_type ?? {};
  const maxTypeCount = Math.max(...Object.values(byType), 1);

  const matchCols = [
    { field: "id", headerName: "ID", width: 80 },
    { field: "player_a", headerName: "Player A", flex: 2 },
    { field: "player_b", headerName: "Player B", flex: 2 },
    { field: "tournament", headerName: "Tournament", flex: 1.5 },
    {
      field: "status",
      headerName: "Status",
      width: 120,
      cellRenderer: (p: any) => {
        const s = p.value;
        if (s === "LIVE") return <Badge variant="success">LIVE</Badge>;
        if (s === "FINISHED") return <Badge variant="outline">FINISHED</Badge>;
        if (s === "SCHEDULED") return <Badge className="bg-blue-600/20 text-blue-400 border-blue-600/30">SCHEDULED</Badge>;
        return <Badge variant="outline">{s}</Badge>;
      },
    },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Registry</h1>

      <div className="grid grid-cols-3 gap-4">
        <StatCard
          title="Total Entities"
          value={summary.isLoading ? "—" : s?.total_entities ?? "—"}
          icon={<BookOpen className="h-4 w-4" />}
        />
        <StatCard
          title="Last Updated"
          value={summary.isLoading ? "—" : s?.last_updated ? new Date(s.last_updated).toLocaleString() : "—"}
          icon={<Users className="h-4 w-4" />}
        />
        <StatCard
          title="Status Types"
          value={Object.keys(byType).length}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Status Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          {summary.isLoading ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : Object.keys(byType).length === 0 ? (
            <p className="text-sm text-slate-500">No status data</p>
          ) : (
            <div className="space-y-2">
              {Object.entries(byType).map(([status, count]) => (
                <div key={status} className="flex items-center gap-3">
                  <span className="w-20 text-xs text-slate-400">{status}</span>
                  <div className="flex-1">
                    <div className="h-5 w-full overflow-hidden rounded bg-slate-800">
                      <div
                        className={`h-full rounded transition-all ${
                          statusColors[status] || "bg-slate-600"
                        }`}
                        style={{ width: `${(count / maxTypeCount) * 100}%` }}
                      />
                    </div>
                  </div>
                  <span className="w-12 text-right font-mono text-xs text-slate-300">{count}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm">Explore Matches</CardTitle>
          <Input
            placeholder="Search registry..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-64"
          />
        </CardHeader>
        <CardContent>
          {matches.isLoading ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : !matches.data || matches.data.length === 0 ? (
            <p className="text-sm text-slate-500">No matches found</p>
          ) : (
            <DataTable
              rowData={matches.data}
              columnDefs={matchCols}
              height={400}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
