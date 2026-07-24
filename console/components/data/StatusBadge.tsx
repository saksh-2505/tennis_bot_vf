"use client";

import React from "react";
import { Badge } from "@/components/ui/Badge";

// Shared `<StatusBadge>` for tracked_match statuses (LIVE / FINISHED / SCHEDULED /
// DISCOVERED plus any future statuses). Replaces the four copies that existed
// with subtle drift — `MatchCard:14-17` relabeled DISCOVERED as SCHEDULED, the
// others used `bg-blue-600/20` className directly.
//
// Stays conservative on color: green for live, slate for finished, blue for
// not-yet-started, default outline for anything unknown.

interface StatusBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  status: string;
}

const SCHEDULED_STATUSES = new Set(["SCHEDULED", "DISCOVERED", "EXPIRED"]);

export function StatusBadge({ status, ...props }: StatusBadgeProps) {
  if (status === "LIVE") return <Badge variant="success" {...props}>LIVE</Badge>;
  if (status === "FINISHED") return <Badge variant="outline" {...props}>{status}</Badge>;
  if (SCHEDULED_STATUSES.has(status)) return <Badge variant="info" {...props}>{status}</Badge>;
  return <Badge variant="outline" {...props}>{status}</Badge>;
}