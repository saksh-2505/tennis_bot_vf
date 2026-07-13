"use client";

import React, { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api, type MatchOverview } from "@/lib/api";
import { DataTable } from "@/components/data/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Search, RefreshCw } from "lucide-react";

const statusOptions = [
  { label: "All", value: "" },
  { label: "LIVE", value: "LIVE" },
  { label: "FINISHED", value: "FINISHED" },
  { label: "SCHEDULED", value: "SCHEDULED" },
];

const qualityOptions = [
  { label: "All", value: "" },
  { label: "A", value: "A" },
  { label: "B", value: "B" },
  { label: "C", value: "C" },
  { label: "D", value: "D" },
  { label: "F", value: "F" },
];

export default function MatchExplorerPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [quality, setQuality] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const params: Record<string, string> = { page: String(page), page_size: String(pageSize) };
  if (status) params.status = status;
  if (quality) params.quality = quality;
  if (search) params.query = search;

  const { data, isLoading, error, refetch } = useQuery<MatchOverview[]>({
    queryKey: ["searchMatches", params],
    queryFn: () => api.searchMatches(params),
  });

  const columnDefs = [
    {
      field: "id",
      headerName: "ID",
      width: 80,
      cellRenderer: (params: any) => (
        <span className="font-mono text-xs text-slate-400">{params.value}</span>
      ),
    },
    { field: "player_a", headerName: "Player A", flex: 2 },
    { field: "player_b", headerName: "Player B", flex: 2 },
    { field: "tournament", headerName: "Tournament", flex: 1.5 },
    { field: "round", headerName: "Round", flex: 1 },
    {
      field: "status",
      headerName: "Status",
      width: 120,
      cellRenderer: (params: any) => {
        const s = params.value;
        if (s === "LIVE") return <Badge variant="success">LIVE</Badge>;
        if (s === "FINISHED") return <Badge variant="outline">FINISHED</Badge>;
        if (s === "SCHEDULED") return <Badge className="bg-blue-600/20 text-blue-400 border-blue-600/30">SCHEDULED</Badge>;
        return <Badge variant="outline">{s}</Badge>;
      },
    },
    {
      field: "quality_grade",
      headerName: "Quality",
      width: 100,
      cellRenderer: (params: any) => {
        if (!params.value) return null;
        return <Badge variant="outline">{params.value}</Badge>;
      },
    },
    {
      field: "odds_avg",
      headerName: "Odds Avg",
      width: 110,
      valueFormatter: (params: any) => (params.value != null ? params.value.toFixed(2) : "—"),
    },
  ];

  const onRowClicked = useCallback(
    (event: any) => {
      router.push(`/matches/${event.data.id}`);
    },
    [router]
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-100">Match Explorer</h1>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-3 w-3" />
          Refresh
        </Button>
      </div>

      <div className="flex items-end gap-3">
        <div className="flex-1">
          <label className="mb-1 block text-xs text-slate-400">Search</label>
          <Input
            placeholder="Search by player, tournament..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        <div className="w-40">
          <label className="mb-1 block text-xs text-slate-400">Status</label>
          <Select
            options={statusOptions}
            value={status}
            onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          />
        </div>
        <div className="w-40">
          <label className="mb-1 block text-xs text-slate-400">Quality</label>
          <Select
            options={qualityOptions}
            value={quality}
            onChange={(e) => { setQuality(e.target.value); setPage(1); }}
          />
        </div>
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading matches</p>
      ) : !data || data.length === 0 ? (
        <p className="text-sm text-slate-500">No matches found</p>
      ) : (
        <DataTable
          rowData={data}
          columnDefs={columnDefs}
          height={600}
        />
      )}

      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500">
          {data?.length ?? 0} results
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
