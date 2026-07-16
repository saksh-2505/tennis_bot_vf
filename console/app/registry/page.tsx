"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type RegistrySummary } from "@/lib/api";
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

  const matches = useQuery({
    queryKey: ["searchMatches", search],
    queryFn: () => api.searchMatches(search ? { player: search } : {}),
  });

  const s = summary.data;
  const byStatus = s?.by_status ?? {};
  const matchItems = matches.data?.items ?? [];
  const maxStatusCount = Math.max(...Object.values(byStatus), 1);

  const matchCols = [
    { field: "id", headerName: "ID", width: 80 },
    { field: "player1_name", headerName: "Player 1", flex: 2 },
    { field: "player2_name", headerName: "Player 2", flex: 2 },
    { field: "tournament", headerName: "Tournament", flex: 1.5 },
    {
      field: "status",
      headerName: "Status",
      width: 120,
      cellRenderer: (p: any) => {
        const s = p.value;
        if (s === "LIVE") return <Badge variant="success">LIVE</Badge>;
        if (s === "FINISHED") return <Badge variant="outline">FINISHED</Badge>;
        if (s === "SCHEDULED" || s === "DISCOVERED")
          return <Badge className="bg-blue-600/20 text-blue-400 border-blue-600/30">{s}</Badge>;
        return <Badge variant="outline">{s}</Badge>;
      },
    },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Registry</h1>

      <div className="grid grid-cols-2 gap-4">
        <StatCard
          title="Total Tracked"
          value={summary.isLoading ? "—" : s?.total ?? "—"}
          icon={<BookOpen className="h-4 w-4" />}
        />
        <StatCard
          title="Status Types"
          value={Object.keys(byStatus).length}
          icon={<Users className="h-4 w-4" />}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Status Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          {summary.isLoading ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : Object.keys(byStatus).length === 0 ? (
            <p className="text-sm text-slate-500">No status data</p>
          ) : (
            <div className="space-y-2">
              {Object.entries(byStatus).map(([status, count]) => (
                <div key={status} className="flex items-center gap-3">
                  <span className="w-20 text-xs text-slate-400">{status}</span>
                  <div className="flex-1">
                    <div className="h-5 w-full overflow-hidden rounded bg-slate-800">
                      <div
                        className={`h-full rounded transition-all ${
                          statusColors[status] || "bg-slate-600"
                        }`}
                        style={{ width: `${(count / maxStatusCount) * 100}%` }}
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
            placeholder="Search by player name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-64"
          />
        </CardHeader>
        <CardContent>
          {matches.isLoading ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : matchItems.length === 0 ? (
            <p className="text-sm text-slate-500">No matches found</p>
          ) : (
            <DataTable rowData={matchItems} columnDefs={matchCols} height={400} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
