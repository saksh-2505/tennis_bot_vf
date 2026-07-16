"use client";

import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface ScoreTimelineProps {
  scores: Array<{
    timestamp: string;
    set_score_a: number | null;
    set_score_b: number | null;
    game_score_a: number | null;
    game_score_b: number | null;
    [key: string]: any;
  }>;
  odds?: any[];
}

export function ScoreTimeline({ scores, odds }: ScoreTimelineProps) {
  const chartData = scores.map((s) => ({
    time: new Date(s.timestamp).toLocaleTimeString(),
    gameA: s.game_score_a ?? 0,
    gameB: s.game_score_b ?? 0,
    setA: s.set_score_a ?? 0,
    setB: s.set_score_b ?? 0,
  }));

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <h3 className="mb-4 text-sm font-medium text-slate-300">Game Score Progression</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgb(51, 65, 85)" />
          <XAxis
            dataKey="time"
            stroke="rgb(100, 116, 139)"
            tick={{ fontSize: 11, fill: "rgb(148, 163, 184)" }}
          />
          <YAxis
            stroke="rgb(100, 116, 139)"
            tick={{ fontSize: 11, fill: "rgb(148, 163, 184)" }}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "rgb(15, 23, 42)",
              border: "1px solid rgb(51, 65, 85)",
              borderRadius: "6px",
              fontSize: "12px",
              color: "rgb(226, 232, 240)",
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="gameA"
            name="Games A"
            stroke="rgb(52, 211, 153)"
            strokeWidth={2}
            dot={{ r: 3, fill: "rgb(52, 211, 153)" }}
          />
          <Line
            type="monotone"
            dataKey="gameB"
            name="Games B"
            stroke="rgb(96, 165, 250)"
            strokeWidth={2}
            dot={{ r: 3, fill: "rgb(96, 165, 250)" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
