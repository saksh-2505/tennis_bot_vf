"use client";

import React from "react";
import { Badge } from "@/components/ui/Badge";

// Shared `<SeverityBadge>` for incident/timeline/log severity.
// Replaces the three near-verbatim copies (timeline:13-17, logs:14-18,
// incidents:61-67) — all rendered the same red/yellow/outline mapping but
// inlined, so each had drifted separately.

interface SeverityBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  level: string;
}

export function SeverityBadge({ level, ...props }: SeverityBadgeProps) {
  if (level === "CRITICAL" || level === "ERROR")
    return <Badge variant="destructive" {...props}>{level}</Badge>;
  if (level === "WARNING") return <Badge variant="warning" {...props}>{level}</Badge>;
  if (level === "INFO") return <Badge variant="info" {...props}>{level}</Badge>;
  return <Badge variant="outline" {...props}>{level ?? "—"}</Badge>;
}