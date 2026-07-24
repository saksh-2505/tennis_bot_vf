"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface TabsContextValue {
  value: string;
  onValueChange: (value: string) => void;
}

const TabsContext = React.createContext<TabsContextValue | null>(null);

interface TabsProps {
  defaultValue: string;
  value?: string;
  onValueChange?: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}

function Tabs({ defaultValue, value: controlledValue, onValueChange, children, className }: TabsProps) {
  const [internalValue, setInternalValue] = React.useState(defaultValue);
  const value = controlledValue !== undefined ? controlledValue : internalValue;
  // Fix: previously `setValue = onValueChange || setInternalValue` — if a caller
  // passed `onValueChange` but NOT `value`, clicking a tab would notify the prop
  // but never update internal state, leaving the UI stuck on the initial tab.
  // Now we always keep internal state synced and propagate to the optional cb.
  const setValue = (next: string) => {
    setInternalValue(next);
    onValueChange?.(next);
  };
  // Controlled path: when `value` is supplied, sync internal state to it.
  React.useEffect(() => {
    if (controlledValue !== undefined) setInternalValue(controlledValue);
  }, [controlledValue]);
  return (
    <TabsContext.Provider value={{ value, onValueChange: setValue }}>
      <div className={className} role="tablist">{children}</div>
    </TabsContext.Provider>
  );
}

function TabsList({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={cn("inline-flex h-9 items-center justify-center rounded-lg bg-slate-800 p-1 text-slate-400", className)}>
      {children}
    </div>
  );
}

function TabsTrigger({ value, className, children }: { value: string; className?: string; children: React.ReactNode }) {
  const ctx = React.useContext(TabsContext);
  const active = ctx?.value === value;
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      aria-controls={`tabpanel-${value}`}
      id={`tab-${value}`}
      onClick={() => ctx?.onValueChange(value)}
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500",
        active && "bg-slate-900 text-slate-100 shadow",
        className
      )}
    >
      {children}
    </button>
  );
}

// Keep TabsContent MOUNTED (CSS-hidden) instead of returning null when inactive.
// Previously: toggling match-detail Scores↔Odds tabs unmounted the AG Grid,
// wiping scroll/sort/filter state on every switch.
function TabsContent({ value, className, children }: { value: string; className?: string; children: React.ReactNode }) {
  const ctx = React.useContext(TabsContext);
  const active = ctx?.value === value;
  return (
    <div
      id={`tabpanel-${value}`}
      role="tabpanel"
      aria-labelledby={`tab-${value}`}
      hidden={!active}
      className={cn("mt-2", active ? "block" : "hidden", className)}
    >
      {children}
    </div>
  );
}

export { Tabs, TabsList, TabsTrigger, TabsContent };
