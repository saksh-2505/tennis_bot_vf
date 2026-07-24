import * as React from "react";
import { cn } from "@/lib/utils";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "info" | "success" | "warning" | "destructive" | "outline";
}

const variants: Record<string, string> = {
  default: "bg-emerald-600/20 text-emerald-400 border-emerald-600/30",
  // `success` previously aliased to `default` — kept for backwards compat,
  // no longer redundant: behaves identically.
  info: "bg-blue-600/20 text-blue-400 border-blue-600/30",
  success: "bg-emerald-600/20 text-emerald-400 border-emerald-600/30",
  warning: "bg-yellow-600/20 text-yellow-400 border-yellow-600/30",
  destructive: "bg-red-600/20 text-red-400 border-red-600/30",
  outline: "border-slate-700 text-slate-300",
};

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };
