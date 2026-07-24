"use client";

import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type RegistrySummary, type RegistryPlayer } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { DataTable } from "@/components/data/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { BookOpen, Users, Search } from "lucide-react";

const statusColors: Record<string, string> = {
  LIVE: "bg-emerald-500", FINISHED: "bg-slate-500",
  SCHEDULED: "bg-blue-500", DISCOVERED: "bg-yellow-500",
};

export default function RegistryPage() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const summary = useQuery<RegistrySummary>({
    queryKey: ["registrySummary"],
    queryFn: () => api.registrySummary(),
  });

  // Now uses the actual Player registry endpoint — the page was previously
  // misnamed: it called `searchMatches` to render matches. The unused
  // `registryPlayers` endpoint and `RegistryPlayer` interface are now wired.
  const players = useQuery<{ items: RegistryPlayer[]; total: number; total_pages: number }>({
    queryKey: ["registryPlayers", { page, page_size: pageSize }],
    queryFn: () => api.registryPlayers({ page: String(page), page_size: String(pageSize) }),
  });

  const s = summary.data;
  const byStatus = s?.by_status ?? {};
  const maxStatusCount = Math.max(...Object.values(byStatus), 1);

  // Client-side filter across the loaded page (registry doesn't expose query
  // search server-side). Keeps the grid responsive below the AG-grid filter.
  const allPlayers = players.data?.items ?? [];
  const filtered = useMemo(() => {
    if (!search.trim()) return allPlayers;
    const q = search.toLowerCase();
    return allPlayers.filter((p) =>
      [p.full_name, p.nationality, p.plays, p.backhand, p.gender].some(
        (v) => v != null && v.toLowerCase().includes(q)
      )
    );
  }, [allPlayers, search]);

  const totalPages = players.data?.total_pages ?? 1;

  const playerCols = useMemo(() => [
    { field: "player_id", headerName: "ID", width: 70 },
    { field: "full_name", headerName: "Player", flex: 2 },
    { field: "nationality", headerName: "Country", width: 120 },
    { field: "age", headerName: "Age", width: 70 },
    {
      field: "current_rank",
      headerName: "Rank",
      width: 80,
      cellRenderer: (p: any) => (p.value != null ? <Badge variant="outline">#{p.value}</Badge> : "—"),
    },
    { field: "career_high_rank", headerName: "Career Hi", width: 90, valueFormatter: (p: any) => (p.value != null ? `#${p.value}` : "—") },
    { field: "gender", headerName: "Tour", width: 70, cellRenderer: (p: any) => (p.value ? <Badge variant="outline">{p.value === "M" ? "ATP" : p.value === "F" ? "WTA" : p.value}</Badge> : "—") },
    { field: "plays", headerName: "Plays", width: 80 },
    { field: "backhand", headerName: "Backhand", width: 100 },
    {
      field: "career_win_percentage",
      headerName: "Win %",
      width: 80,
      valueFormatter: (p: any) => (p.value != null ? `${p.value.toFixed(1)}%` : "—"),
    },
  ], []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Registry</h1>

      <div className="grid grid-cols-2 gap-4">
        <StatCard
          title="Tracked Matches"
          value={summary.isLoading ? "—" : s?.total ?? "—"}
          icon={<BookOpen className="h-4 w-4" />}
        />
        <StatCard
          title="Players in Registry"
          value={players.isLoading ? "—" : players.data?.total ?? "—"}
          icon={<Users className="h-4 w-4" />}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Match Status Distribution</CardTitle>
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
          <CardTitle className="text-sm">Players ({players.data?.total ?? 0})</CardTitle>
          <div className="relative w-64">
            <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
            <Input
              placeholder="Filter by name, country, hand..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-7"
            />
          </div>
        </CardHeader>
        <CardContent>
          {players.isLoading ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : filtered.length === 0 ? (
            <p className="text-sm text-slate-500">No players found</p>
          ) : (
            <DataTable rowData={filtered} columnDefs={playerCols} height={550} />
          )}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500">
          page {page}/{Math.max(totalPages, 1)}
        </span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
