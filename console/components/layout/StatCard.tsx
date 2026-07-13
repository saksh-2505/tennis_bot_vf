import React from "react";
import { cn } from "@/lib/utils";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: "up" | "down" | "neutral";
  color?: string;
}

const trendIcons = {
  up: <ArrowUp className="h-3 w-3 text-emerald-400" />,
  down: <ArrowDown className="h-3 w-3 text-red-400" />,
  neutral: <Minus className="h-3 w-3 text-slate-400" />,
};

export function StatCard({ title, value, subtitle, icon, trend, color }: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-slate-800 bg-slate-900 p-4 shadow-sm",
        color && `border-l-2 border-l-${color}`
      )}
      style={color ? { borderLeftColor: color } : undefined}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400">{title}</span>
        {icon && <span className="text-slate-500">{icon}</span>}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-bold text-slate-100">{value}</span>
        {trend && <span className="flex items-center gap-0.5 text-xs">{trendIcons[trend]}</span>}
      </div>
      {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
    </div>
  );
}
