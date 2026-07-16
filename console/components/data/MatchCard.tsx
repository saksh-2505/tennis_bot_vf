"use client";

import React from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent } from "@/components/ui/Card";
import { formatDate } from "@/lib/utils";
import type { MatchOverview } from "@/lib/api";

export function MatchCard({ match }: { match: MatchOverview }) {
  const statusBadge = (status: string) => {
    if (status === "LIVE") return <Badge variant="success">LIVE</Badge>;
    if (status === "FINISHED") return <Badge variant="outline">FINISHED</Badge>;
    if (status === "SCHEDULED" || status === "DISCOVERED")
      return <Badge className="bg-blue-600/20 text-blue-400 border-blue-600/30">SCHEDULED</Badge>;
    return <Badge variant="outline">{status}</Badge>;
  };

  const hasLiveScore =
    match.live_score_set_a != null || match.live_score_set_b != null ||
    match.live_score_game_a != null || match.live_score_game_b != null;

  return (
    <Link href={`/matches/${match.id}`}>
      <Card className="cursor-pointer transition-colors hover:border-slate-700 hover:bg-slate-800/50">
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span>{match.tournament}</span>
              </div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="font-semibold text-slate-100">{match.player1_name}</span>
                <span className="text-xs text-slate-500">vs</span>
                <span className="font-semibold text-slate-100">{match.player2_name}</span>
              </div>
              {match.status === "LIVE" && hasLiveScore && (
                <div className="mt-2 font-mono text-lg font-bold text-slate-100">
                  {match.live_score_set_a ?? 0}-{match.live_score_set_b ?? 0}{" "}
                  <span className="text-base">
                    ({match.live_score_game_a ?? 0}-{match.live_score_game_b ?? 0})
                  </span>
                  {match.live_score_point && (
                    <span className="ml-2 text-sm text-slate-400">
                      {match.live_score_point}
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
            {match.live_odds_a != null && (
              <span>O: {match.live_odds_a.toFixed(2)}</span>
            )}
            {match.live_odds_b != null && (
              <span>O: {match.live_odds_b.toFixed(2)}</span>
            )}
            {match.live_score_server && (
              <span>Serve: {match.live_score_server}</span>
            )}
            {match.last_score_poll && (
              <span className="ml-auto">{formatDate(match.last_score_poll)}</span>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
