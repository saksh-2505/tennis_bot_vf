"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type DbTable, type DbTableDetail } from "@/lib/api";
import { DataTable } from "@/components/data/DataTable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Database, Table, Search } from "lucide-react";

export default function DatabasePage() {
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [rowFilter, setRowFilter] = useState("");

  const tables = useQuery<DbTable[]>({
    queryKey: ["dbTables"],
    queryFn: () => api.dbTables(),
  });

  const tableDetail = useQuery<DbTableDetail>({
    queryKey: ["dbTable", selectedTable],
    queryFn: () => api.dbTable(selectedTable!),
    enabled: !!selectedTable,
  });

  const tableCols = [
    { field: "name", headerName: "Table Name", flex: 2 },
    { field: "schema", headerName: "Schema", flex: 1 },
    { field: "row_count", headerName: "Rows", width: 120, type: "numericColumn" },
    { field: "size", headerName: "Size", width: 100 },
    { field: "last_vacuum", headerName: "Last Vacuum", flex: 1.5 },
  ];

  const sampleRows = tableDetail.data?.sample_rows ?? [];
  const filteredRows = rowFilter
    ? sampleRows.filter((row) =>
        Object.values(row).some((val) =>
          String(val).toLowerCase().includes(rowFilter.toLowerCase())
        )
      )
    : sampleRows;

  const detailCols = tableDetail.data?.columns.map((col) => ({
    field: col.name,
    headerName: col.name,
    flex: 1,
    minWidth: 120,
  })) ?? [];

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
                  Tables ({tables.data?.length ?? 0})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {tables.data?.map((t) => (
                  <button
                    key={t.name}
                    onClick={() => setSelectedTable(t.name)}
                    className={`flex w-full items-center justify-between rounded px-3 py-2 text-left text-sm transition-colors ${
                      selectedTable === t.name
                        ? "bg-emerald-600/20 text-emerald-400"
                        : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Table className="h-3 w-3" />
                      <span>{t.name}</span>
                    </div>
                    <Badge variant="outline" className="text-xs">{t.row_count}</Badge>
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
                  <div className="flex items-center gap-3">
                    <h2 className="font-semibold text-slate-200">{selectedTable}</h2>
                    <Badge variant="outline">
                      {tableDetail.data?.row_count ?? 0} rows
                    </Badge>
                    <span className="text-xs text-slate-500">
                      {tableDetail.data?.columns.length ?? 0} columns
                    </span>
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
