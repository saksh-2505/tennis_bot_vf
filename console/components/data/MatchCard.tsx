"use client";

import React from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/Card";
import { StatusBadge } from "@/components/data/StatusBadge";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";
import type { MatchOverview } from "@/lib/api";

function MatchCardImpl({ match }: { match: MatchOverview }) {
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
              <StatusBadge status={match.status} />
              {match.quality_grade && (
                <Badge variant="outline" className="text-xs">
                  Q: {match.quality_grade}
                </Badge>
              )}
            </div>
          </div>
          <div className="mt-3 flex items-center gap-4 text-xs text-slate-500">
            {match.live_odds_a != null && (
              <span>A: {match.live_odds_a.toFixed(2)}</span>
            )}
            {match.live_odds_b != null && (
              <span>B: {match.live_odds_b.toFixed(2)}</span>
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

// Memo + stable comparator: live overview re-fetches every 5s with brand-new
// array refs. Without memo every MatchCard re-renders regardless of whether
// its underlying match row changed. We compare by id + the volatile fields
// that actually update (scores, odds, server, poll timestamps, quality_grade).
type MatchCardProps = { match: MatchOverview };
function matchChanged(prev: Readonly<MatchCardProps>, next: Readonly<MatchCardProps>): boolean {
  const p = prev.match;
  const n = next.match;
  return (
    p.id === n.id &&
    p.status === n.status &&
    p.live_score_set_a === n.live_score_set_a &&
    p.live_score_set_b === n.live_score_set_b &&
    p.live_score_game_a === n.live_score_game_a &&
    p.live_score_game_b === n.live_score_game_b &&
    p.live_score_point === n.live_score_point &&
    p.live_score_server === n.live_score_server &&
    p.live_odds_a === n.live_odds_a &&
    p.live_odds_b === n.live_odds_b &&
    p.last_score_poll === n.last_score_poll &&
    p.last_odds_poll === n.last_odds_poll &&
    p.quality_grade === n.quality_grade
  );
}

export const MatchCard = React.memo(MatchCardImpl, matchChanged);
