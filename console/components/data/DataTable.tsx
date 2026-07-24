"use client";

import React, { useMemo, useCallback } from "react";
import { AgGridReact } from "ag-grid-react";
import { ColDef, RowClickedEvent } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

interface DataTableProps {
  rowData: any[];
  columnDefs: ColDef[];
  pagination?: boolean;
  height?: number;
  /** Row click handler — opens detail pages (Match, Incident, …) when wired by the caller. */
  onRowClicked?: (event: RowClickedEvent) => void;
  /** Override the row-id getter (default: `data.id`). Stable identity prevents
      row flicker / selection loss when React Query hands AG Grid new array refs on refetch. */
  getRowId?: (params: { data: any }) => string;
}

export function DataTable({
  rowData,
  columnDefs,
  pagination = true,
  height = 500,
  onRowClicked,
  getRowId,
}: DataTableProps) {
  const defaultColDef = useMemo<ColDef>(
    () => ({
      sortable: true,
      filter: true,
      resizable: true,
      flex: 1,
      minWidth: 100,
    }),
    []
  );

  // Default identity: `data.id` (almost every entity has a numeric `id`).
  // Stable identity means AG Grid keeps scroll/sort/selection across refetches.
  const rowIdGetter = useMemo(
    () => getRowId ?? ((p: { data: any }) => (p.data?.id != null ? String(p.data.id) : "")),
    [getRowId]
  );

  const handleRowClicked = useCallback((e: RowClickedEvent) => {
    onRowClicked?.(e);
  }, [onRowClicked]);

  return (
    <div className="ag-theme-alpine-dark" style={{ height, width: "100%" }}>
      <AgGridReact
        rowData={rowData}
        columnDefs={columnDefs}
        defaultColDef={defaultColDef}
        pagination={pagination}
        paginationPageSize={50}
        paginationPageSizeSelector={[25, 50, 100, 200]}
        domLayout="normal"
        animateRows={true}
        enableCellTextSelection={true}
        suppressRowClickSelection={true}
        getRowId={rowIdGetter}
        onRowClicked={handleRowClicked}
      />
    </div>
  );
}
