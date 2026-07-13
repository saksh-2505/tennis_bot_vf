import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(d: string | null) {
  return d ? new Date(d).toLocaleString() : '—';
}

export function formatDuration(min: number | null) {
  return min ? `${min} min` : '—';
}

export function formatPct(v: number | null) {
  return v != null ? `${v.toFixed(1)}%` : '—';
}

export function statusColor(status: string) {
  const map: Record<string, string> = {
    LIVE: 'text-green-400',
    FINISHED: 'text-slate-400',
    SCHEDULED: 'text-blue-400',
    DISCOVERED: 'text-yellow-400',
  };
  return map[status] || 'text-slate-400';
}

export function qualityColor(grade: string | null) {
  const map: Record<string, string> = {
    A: 'text-green-400',
    B: 'text-blue-400',
    C: 'text-yellow-400',
    D: 'text-orange-400',
    F: 'text-red-400',
  };
  return map[grade || ''] || 'text-slate-400';
}

export function severityColor(severity: string) {
  const map: Record<string, string> = {
    CRITICAL: 'text-red-400',
    ERROR: 'text-red-400',
    WARNING: 'text-yellow-400',
    INFO: 'text-blue-400',
  };
  return map[severity] || 'text-slate-400';
}
