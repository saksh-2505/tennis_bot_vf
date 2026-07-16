"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type DiscoverySummary } from "@/lib/api";
import { StatCard } from "@/components/layout/StatCard";
import { Compass, Satellite } from "lucide-react";

export default function DiscoveryPage() {
  const { data, isLoading, error } = useQuery<DiscoverySummary>({
    queryKey: ["discoverySummary"],
    queryFn: () => api.discoverySummary(),
    refetchInterval: 60_000,
  });

  const s = data;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Discovery</h1>

      <div className="grid grid-cols-2 gap-4">
        <StatCard
          title="Flashscore Matches"
          value={isLoading ? "—" : s?.flashscore_total ?? "—"}
          icon={<Compass className="h-4 w-4" />}
        />
        <StatCard
          title="Betting Site Matches"
          value={isLoading ? "—" : s?.bettingsite_total ?? "—"}
          icon={<Satellite className="h-4 w-4" />}
        />
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading discovery summary</p>
      ) : !s ? (
        <p className="text-sm text-slate-500">No discovery data</p>
      ) : null}
    </div>
  );
}
