"use client";

import React, { useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { ColDef } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

interface DataTableProps {
  rowData: any[];
  columnDefs: ColDef[];
  pagination?: boolean;
  height?: number;
}

export function DataTable({
  rowData,
  columnDefs,
  pagination = true,
  height = 500,
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
      />
    </div>
  );
}
