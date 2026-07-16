"use client";

import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api, type SearchResult } from "@/lib/api";
import { Input } from "@/components/ui/Input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Search, ArrowRight, Loader2 } from "lucide-react";

const typeGroupLabel: Record<string, string> = {
  match: "Matches",
  player: "Players",
  incident: "Incidents",
  event: "Events",
  tournament: "Tournaments",
};

export default function SearchPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
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

  const grouped: Record<string, any[]> = {};
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
                {items.map((item, i) => (
                  <Card
                    key={`${item.type}-${item.id}-${i}`}
                    className="cursor-pointer transition-colors hover:border-slate-700"
                    onClick={() => {
                      if (item.url) router.push(item.url);
                    }}
                  >
                    <CardContent className="flex items-center justify-between p-4">
                      <div>
                        <p className="text-sm font-medium text-slate-200">{item.title}</p>
                        {item.description && (
                          <p className="mt-1 text-xs text-slate-500">{item.description}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-slate-500">
                        <Badge variant="outline">{item.type}</Badge>
                        <ArrowRight className="h-3 w-3" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
