"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/Table";
import { cn } from "@/lib/utils";

export interface DataTableColumn<T> {
  key: string;
  header: string;
  render: (row: T) => React.ReactNode;
  sortValue?: (row: T) => string | number | null;
  className?: string;
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  getRowId: (row: T, index: number) => string | number;
  onRowClick?: (row: T) => void;
  pagination?: { page: number; totalPages: number; onPageChange: (page: number) => void };
  emptyMessage?: string;
  rowClassName?: (row: T) => string | undefined;
}

/** Reusable sortable/paginated table (`docs/FRONTEND_SPEC.md` §24), built on
 * the `Table` primitive. Sorting is client-side over the current page's
 * `rows` (the backend's list endpoints don't expose a generic `?sort=`
 * query param yet, per `docs/API.md` cross-cutting notes — "exact
 * query-param names finalized... before Phase 11 integration closes").
 * Pagination is server-driven via the `pagination` prop's callback. */
export function DataTable<T>({
  columns,
  rows,
  getRowId,
  onRowClick,
  pagination,
  emptyMessage,
  rowClassName,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const sortedRows = useMemo(() => {
    if (!sortKey) return rows;
    const column = columns.find((c) => c.key === sortKey);
    if (!column?.sortValue) return rows;
    const withValues = rows.map((row) => ({ row, value: column.sortValue!(row) }));
    withValues.sort((a, b) => {
      if (a.value === null) return 1;
      if (b.value === null) return -1;
      if (a.value < b.value) return sortDir === "asc" ? -1 : 1;
      if (a.value > b.value) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return withValues.map((w) => w.row);
  }, [rows, sortKey, sortDir, columns]);

  function toggleSort(column: DataTableColumn<T>) {
    if (!column.sortValue) return;
    if (sortKey === column.key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(column.key);
      setSortDir("asc");
    }
  }

  if (rows.length === 0 && emptyMessage) {
    return <p className="py-8 text-center text-sm text-text-muted">{emptyMessage}</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      <Table>
        <Thead>
          <Tr>
            {columns.map((column) => (
              <Th
                key={column.key}
                className={cn(column.sortValue && "cursor-pointer select-none", column.className)}
                onClick={() => toggleSort(column)}
                aria-sort={sortKey === column.key ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
              >
                <span className="inline-flex items-center gap-1">
                  {column.header}
                  {column.sortValue && sortKey === column.key && (
                    <span aria-hidden="true">{sortDir === "asc" ? "▲" : "▼"}</span>
                  )}
                </span>
              </Th>
            ))}
          </Tr>
        </Thead>
        <Tbody>
          {sortedRows.map((row, index) => (
            <Tr
              key={getRowId(row, index)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={cn(onRowClick && "cursor-pointer", rowClassName?.(row))}
            >
              {columns.map((column) => (
                <Td key={column.key} className={column.className}>
                  {column.render(row)}
                </Td>
              ))}
            </Tr>
          ))}
        </Tbody>
      </Table>
      {pagination && pagination.totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-text-muted">
          <span>
            Page {pagination.page} of {pagination.totalPages}
          </span>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="secondary"
              disabled={pagination.page <= 1}
              onClick={() => pagination.onPageChange(pagination.page - 1)}
            >
              Previous
            </Button>
            <Button
              size="sm"
              variant="secondary"
              disabled={pagination.page >= pagination.totalPages}
              onClick={() => pagination.onPageChange(pagination.page + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
