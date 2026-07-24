"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type MatchOverview } from "@/lib/api";
import { MatchCard } from "@/components/data/MatchCard";
import { Badge } from "@/components/ui/Badge";
import { Radio, RefreshCw } from "lucide-react";

export default function LiveMatchesPage() {
  const { data, isLoading, error, isFetching } = useQuery<MatchOverview[]>({
    queryKey: ["liveMatches"],
    queryFn: () => api.liveMatches(),
    refetchInterval: 5000,
    // Don't keep hammering the API when the user is on another tab.
    refetchIntervalInBackground: false,
  });

  const matches = data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-slate-100">Live Matches</h1>
          {matches.length > 0 && (
            <Badge variant="success">{matches.length} live</Badge>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          {isFetching && (
            <>
              <RefreshCw className="h-3 w-3 animate-spin" />
              <span>Auto-refreshing...</span>
            </>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <RefreshCw className="h-4 w-4 animate-spin" />
          Loading live matches...
        </div>
      ) : error ? (
        <p className="text-sm text-red-400">Error loading live matches</p>
      ) : matches.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-slate-800 bg-slate-900 py-16">
          <Radio className="mb-3 h-8 w-8 text-slate-600" />
          <p className="text-sm text-slate-500">No live matches</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {matches.map((match) => (
            <MatchCard key={match.id} match={match} />
          ))}
        </div>
      )}
    </div>
  );
}
