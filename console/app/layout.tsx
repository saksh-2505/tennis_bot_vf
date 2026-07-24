"use client";

import React, { useState, type FormEvent, type ChangeEvent } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useQuery, QueryClient, QueryClientProvider, QueryCache } from "@tanstack/react-query";
import toast, { Toaster } from "react-hot-toast";
import { Sidebar } from "@/components/layout/Sidebar";
import { api } from "@/lib/api";
import type { PlatformOverview, ObservabilityHealth } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Search } from "lucide-react";
import "@/app/globals.css";

const queryClient = new QueryClient({
  // QueryCache#onError surfaces background-fetch failures (polls, refetches)
  // as toasts — previously the <Toaster> was mounted but never fed any message.
  queryCache: new QueryCache({
    onError: (error, query) => {
      if (query.state.data !== undefined) {
        toast.error(
          `${query.queryKey.join("/")}: ${error instanceof Error ? error.message : "Request failed"}`,
          { duration: 5000 },
        );
      }
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

function TopBar() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");

  const overview = useQuery<PlatformOverview>({
    queryKey: ["overview"],
    queryFn: () => api.overview(),
    refetchInterval: 30_000,
    staleTime: 10_000,
    refetchIntervalInBackground: false,
  });

  // Real DB health — previously hardcoded to green "Connected" regardless of state.
  const health = useQuery<ObservabilityHealth>({
    queryKey: ["observabilityHealth"],
    queryFn: () => api.observabilityHealth(),
    refetchInterval: 30_000,
    staleTime: 10_000,
    refetchIntervalInBackground: false,
  });

  const dbConnected = health.data?.db === true;
  const dbLoading = health.isLoading;
  const lastRefresh = overview.dataUpdatedAt
    ? new Date(overview.dataUpdatedAt).toLocaleTimeString()
    : "—";

  const onSearchSubmit = (e: FormEvent) => {
    e.preventDefault();
    const q = searchQuery.trim();
    router.push(q ? `/search?q=${encodeURIComponent(q)}` : "/search");
  };

  return (
    <div className="mb-6 flex flex-wrap items-center gap-4 rounded-lg border border-slate-800 bg-slate-900 px-4 py-2 text-sm">
      <div className="flex items-center gap-2">
        <div
          className={cn(
            "h-2 w-2 rounded-full",
            dbLoading
              ? "bg-slate-500 animate-pulse"
              : dbConnected
                ? "bg-emerald-500"
                : "bg-red-500 animate-pulse",
          )}
        />
        <span className="text-slate-400">DB:</span>
        <span
          className={cn(
            "font-medium",
            dbLoading ? "text-slate-300" : dbConnected ? "text-emerald-400" : "text-red-400",
          )}
        >
          {dbLoading ? "Checking…" : dbConnected ? "Connected" : "Disconnected"}
        </span>
      </div>
      <div className="text-slate-600">|</div>
      <div className="flex items-center gap-2">
        <span className="text-slate-400">Live Matches:</span>
        <span className="font-medium text-slate-200">
          {overview.isLoading ? "—" : overview.data?.live_matches ?? "—"}
        </span>
      </div>
      <div className="text-slate-600">|</div>
      <div className="flex items-center gap-2">
        <span className="text-slate-400">Finished:</span>
        <span className="font-medium text-slate-200">
          {overview.isLoading ? "—" : overview.data?.finished_matches ?? "—"}
        </span>
      </div>
      <div className="text-slate-600">|</div>
      <div className="flex items-center gap-2">
        <span className="text-slate-400">Last Refresh:</span>
        {/* Now reflects the actual dataUpdatedAt of the overview query, not wall-clock. */}
        <span className="font-medium text-slate-200">{lastRefresh}</span>
      </div>
      {/* Global header search — routes to /search?q=… on submit (one keystroke to
          reach any match, player, or incident, without hunting the sidebar). */}
      <form onSubmit={onSearchSubmit} className="ml-auto relative">
        <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
          placeholder="Search matches, players..."
          className="w-64 rounded-md border border-slate-700 bg-slate-800/50 py-1 pl-8 pr-3 text-xs text-slate-200 placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none"
        />
      </form>
    </div>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <html lang="en">
      <head>
        <title>Sports Trading Platform — Dev Console</title>
        <meta name="description" content="Developer Console for Sports Trading Platform" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className="bg-slate-950 text-slate-100 antialiased">
        <QueryClientProvider client={queryClient}>
          <div className="flex min-h-screen">
            <Sidebar pathname={pathname} />
            <main className="ml-[280px] flex-1 p-6">
              <TopBar />
              {children}
            </main>
          </div>
          <Toaster
            position="bottom-right"
            toastOptions={{
              style: {
                background: "rgb(15, 23, 42)",
                color: "rgb(226, 232, 240)",
                border: "1px solid rgb(51, 65, 85)",
                fontSize: "13px",
              },
            }}
          />
        </QueryClientProvider>
      </body>
    </html>
  );
}
