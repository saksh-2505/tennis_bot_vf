"use client";

import React, { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api, type DbTablesResponse, type DbTableDetail } from "@/lib/api";
import { DataTable } from "@/components/data/DataTable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Database, Table, Search, ExternalLink } from "lucide-react";

// Tables whose primary key (and `id`/`incident_id` column) maps directly to a
// rich page in the console — clicking a row navigates instead of being a dead-end.
const TABLE_DEEPLINK: Record<string, { idColumn: string; path: (id: string | number) => string }> = {
  tracked_matches: { idColumn: "id", path: (id) => `/matches/${id}` },
  completed_matches: { idColumn: "tracked_match_id", path: (id) => `/matches/${id}` },
  incidents: { idColumn: "incident_id", path: (id) => `/incidents?incident_id=${id}` },
};

export default function DatabasePage() {
  const router = useRouter();
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [rowFilter, setRowFilter] = useState("");

  const tables = useQuery<DbTablesResponse>({
    queryKey: ["dbTables"],
    queryFn: () => api.dbTables(),
  });

  const tableList = tables.data?.tables ?? [];

  const tableDetail = useQuery<DbTableDetail>({
    queryKey: ["dbTable", selectedTable],
    queryFn: () => api.dbTable(selectedTable!),
    enabled: !!selectedTable,
  });

  const sampleRows = tableDetail.data?.rows ?? [];
  const filteredRows = useMemo(
    () =>
      rowFilter
        ? sampleRows.filter((row) =>
            Object.values(row).some((val) =>
              String(val ?? "").toLowerCase().includes(rowFilter.toLowerCase())
            )
          )
        : sampleRows,
    [sampleRows, rowFilter]
  );

  const deeplink = selectedTable ? TABLE_DEEPLINK[selectedTable] : undefined;

  const onRowClicked = (e: any) => {
    if (!deeplink) return;
    const id = e.data?.[deeplink.idColumn];
    if (id != null) router.push(deeplink.path(id));
  };

  const detailCols = useMemo(
    () =>
      tableDetail.data?.columns.map((colName: string) => ({
        field: colName,
        headerName: colName,
        flex: 1,
        minWidth: 120,
        // Render `id` / `incident_id` columns of deeplinkable tables with a hover affordance.
        cellRenderer:
          deeplink && colName === deeplink.idColumn
            ? (p: any) => (
              <span className="flex items-center gap-1 text-emerald-400">
                {String(p.value ?? "")}
                <ExternalLink className="h-3 w-3 opacity-60" />
              </span>
            )
            : undefined,
      })) ?? [],
    [tableDetail.data, deeplink]
  );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-100">Database Explorer</h1>

      {tables.isLoading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : tables.error ? (
        <p className="text-sm text-red-400">Error loading database tables</p>
      ) : (
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-1">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Database className="h-4 w-4" />
                  Tables ({tableList.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {tableList.map((t) => (
                  <button
                    key={t.table}
                    onClick={() => { setSelectedTable(t.table); setRowFilter(""); }}
                    className={`flex w-full items-center justify-between rounded px-3 py-2 text-left text-sm transition-colors ${
                      selectedTable === t.table
                        ? "bg-emerald-600/20 text-emerald-400"
                        : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Table className="h-3 w-3" />
                      <span>{t.table}</span>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {t.row_count.toLocaleString()}
                    </Badge>
                  </button>
                ))}
              </CardContent>
            </Card>
          </div>

          <div className="col-span-2">
            {!selectedTable ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-16">
                  <Table className="mb-3 h-8 w-8 text-slate-600" />
                  <p className="text-sm text-slate-500">Select a table to view its data</p>
                </CardContent>
              </Card>
            ) : tableDetail.isLoading ? (
              <p className="text-sm text-slate-500">Loading table data...</p>
            ) : tableDetail.error ? (
              <p className="text-sm text-red-400">Error loading table: {selectedTable}</p>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex flex-wrap items-center gap-3">
                    <h2 className="font-semibold text-slate-200">{selectedTable}</h2>
                    <Badge variant="outline">
                      {(tableDetail.data?.rows.length ?? 0).toLocaleString()} rows shown
                    </Badge>
                    <span className="text-xs text-slate-500">
                      {tableDetail.data?.columns.length ?? 0} columns
                    </span>
                    {deeplink && (
                      <span className="text-xs text-emerald-400/70">
                        click a row to open rich view
                      </span>
                    )}
                  </div>
                  <div className="relative w-64">
                    <Search className="absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 text-slate-500" />
                    <Input
                      placeholder="Filter rows..."
                      value={rowFilter}
                      onChange={(e) => setRowFilter(e.target.value)}
                      className="pl-7"
                    />
                  </div>
                </div>

                {filteredRows.length === 0 ? (
                  <p className="text-sm text-slate-500">No rows match the filter</p>
                ) : (
                  <DataTable
                    rowData={filteredRows.slice(0, 50)}
                    columnDefs={detailCols}
                    height={500}
                    onRowClicked={onRowClicked}
                  />
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
