"use client";

import React from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent } from "@/components/ui/Card";
import { statusColor, formatDate, formatPct } from "@/lib/utils";
import type { MatchOverview } from "@/lib/api";

export function MatchCard({ match }: { match: MatchOverview }) {
  const statusBadge = (status: string) => {
    if (status === "LIVE") return <Badge variant="success">LIVE</Badge>;
    if (status === "FINISHED") return <Badge variant="outline">FINISHED</Badge>;
    if (status === "SCHEDULED") return <Badge className="bg-blue-600/20 text-blue-400 border-blue-600/30">SCHEDULED</Badge>;
    return <Badge variant="outline">{status}</Badge>;
  };

  return (
    <Link href={`/matches/${match.id}`}>
      <Card className="cursor-pointer transition-colors hover:border-slate-700 hover:bg-slate-800/50">
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span>{match.tournament}</span>
                <span>·</span>
                <span>{match.round}</span>
              </div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="font-semibold text-slate-100">{match.player_a}</span>
                <span className="text-xs text-slate-500">vs</span>
                <span className="font-semibold text-slate-100">{match.player_b}</span>
              </div>
              {match.status === "LIVE" && (
                <div className="mt-2 font-mono text-lg font-bold text-slate-100">
                  {match.set_score_a}-{match.set_score_b}{" "}
                  <span className="text-base">
                    ({match.game_score_a}-{match.game_score_b})
                  </span>
                  {(match.point_score_a || match.point_score_b) && (
                    <span className="ml-2 text-sm text-slate-400">
                      {match.point_score_a}-{match.point_score_b}
                    </span>
                  )}
                </div>
              )}
            </div>
            <div className="flex flex-col items-end gap-1">
              {statusBadge(match.status)}
              {match.quality_grade && (
                <Badge variant="outline" className="text-xs">
                  Q: {match.quality_grade}
                </Badge>
              )}
            </div>
          </div>
          <div className="mt-3 flex items-center gap-4 text-xs text-slate-500">
            {match.odds_avg != null && (
              <span>Odds: {match.odds_avg.toFixed(2)}</span>
            )}
            {match.odds_ev != null && (
              <span className="text-emerald-400">EV: {formatPct(match.odds_ev)}</span>
            )}
            {match.collector_name && <span>{match.collector_name}</span>}
            {match.last_poll_time && (
              <span className="ml-auto">{formatDate(match.last_poll_time)}</span>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
