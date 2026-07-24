"use client";

import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api, type SearchResult } from "@/lib/api";
import { Input } from "@/components/ui/Input";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Search, ArrowRight, Loader2 } from "lucide-react";

const typeGroupLabel: Record<string, string> = {
  match: "Matches",
  player: "Players",
  incident: "Incidents",
  event: "Events",
  tournament: "Tournaments",
};

// Build a navigation URL from a SearchResult. The backend (`search.py`) returns
// `{type, id, label, match}` — no `url`/`title`/`description` fields despite the
// old page reading them (rendered blanks). Until dedicated player/incident routes
// exist, players & incidents fall back to their listing pages.
function itemUrl(item: SearchResult): string | null {
  switch (item.type) {
    case "match":
      return `/matches/${item.id}`;
    case "player":
      return `/registry`;
    case "incident":
      return `/incidents`;
    default:
      return null;
  }
}

// Short subtitle extracted from the `match` blob the backend returns per type.
function itemDescription(item: SearchResult): string | null {
  const m = item.match;
  if (!m) return null;
  if (item.type === "match") {
    return [m.status, m.betting_market_id ? "market linked" : "no market"].filter(Boolean).join(" · ");
  }
  if (item.type === "player") {
    return [m.nationality, m.current_rank ? `rank #${m.current_rank}` : null, m.gender]
      .filter(Boolean).join(" · ");
  }
  if (item.type === "incident") {
    return [m.severity, m.status, m.category].filter(Boolean).join(" · ");
  }
  return null;
}

export default function SearchPage() {
  const router = useRouter();
  // Seed from `?q=` if the TopBar header search passed a query — the dashboard
  // / any page can now reach search via Enter and pre-populate the box.
  const [query, setQuery] = useState(() => {
    if (typeof window === "undefined") return "";
    const params = new URLSearchParams(window.location.search);
    return params.get("q") ?? "";
  });
  const [debounced, setDebounced] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query), 300);
    return () => clearTimeout(timer);
  }, [query]);

  const { data, isLoading, error } = useQuery({
    queryKey: ["search", debounced],
    queryFn: () => api.search(debounced),
    enabled: debounced.length >= 2,
  });

  const results = data?.results ?? [];

  const grouped: Record<string, SearchResult[]> = {};
  results.forEach((r) => {
    const key = typeGroupLabel[r.type] || r.type || "Other";
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(r);
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Search</h1>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <Input
          placeholder="Search matches, players, incidents..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-10 text-base"
          autoFocus
        />
      </div>

      {debounced.length < 2 ? (
        <p className="text-sm text-slate-500">Type at least 2 characters to search</p>
      ) : isLoading ? (
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Loader2 className="h-4 w-4 animate-spin" />
          Searching...
        </div>
      ) : error ? (
        <p className="text-sm text-red-400">Error searching</p>
      ) : results.length === 0 ? (
        <p className="text-sm text-slate-500">No results for "{debounced}"</p>
      ) : (
        <div className="space-y-6">
          {Object.entries(grouped).map(([group, items]) => (
            <div key={group}>
              <div className="mb-3 flex items-center gap-2">
                <h2 className="text-sm font-semibold text-slate-300">{group}</h2>
                <Badge variant="outline">{items.length}</Badge>
              </div>
              <div className="space-y-2">
                {items.map((item, i) => {
                  const url = itemUrl(item);
                  const desc = itemDescription(item);
                  return (
                    <Card
                      key={`${item.type}-${item.id}-${i}`}
                      className={url ? "cursor-pointer transition-colors hover:border-slate-700" : ""}
                      onClick={() => {
                        if (url) router.push(url);
                      }}
                    >
                      <CardContent className="flex items-center justify-between p-4">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-slate-200">{item.label}</p>
                          {desc && (
                            <p className="mt-1 truncate text-xs text-slate-500">{desc}</p>
                          )}
                        </div>
                        <div className="ml-3 flex shrink-0 items-center gap-2 text-xs text-slate-500">
                          <Badge variant="outline">{item.type}</Badge>
                          {url && <ArrowRight className="h-3 w-3" />}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
