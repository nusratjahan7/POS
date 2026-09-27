"use client";

import * as React from "react";
import type { LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { describeError } from "@/lib/api/client";
import { cn } from "@/lib/utils";

type Align = "left" | "center" | "right";
type Breakpoint = "sm" | "md" | "lg";

export type DataTableColumn<T> = {
  id: string;
  header: React.ReactNode;
  cell: (row: T) => React.ReactNode;
  align?: Align;
  className?: string;
  headClassName?: string;
  /** Hide the column below this breakpoint. */
  hideBelow?: Breakpoint;
};

export type DataTableProps<T> = {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  isLoading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  skeletonRows?: number;
  emptyIcon?: LucideIcon;
  emptyTitle: string;
  emptyDescription?: string;
  className?: string;
};

const ALIGN: Record<Align, string> = {
  left: "text-left",
  center: "text-center",
  right: "text-right",
};

const HIDE_BELOW: Record<Breakpoint, string> = {
  sm: "hidden sm:table-cell",
  md: "hidden md:table-cell",
  lg: "hidden lg:table-cell",
};

/**
 * Presentational table that owns the loading / error / empty states and column
 * alignment, so every list screen renders those the same way.
 */
function DataTable<T>({
  columns,
  rows,
  rowKey,
  isLoading = false,
  error,
  onRetry,
  skeletonRows = 5,
  emptyIcon,
  emptyTitle,
  emptyDescription,
  className,
}: DataTableProps<T>) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-3 py-2">
        {Array.from({ length: skeletonRows }).map((_, index) => (
          <Skeleton key={index} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Could not load data"
        description={describeError(error)}
        action={
          onRetry ? (
            <Button variant="outline" onClick={onRetry}>
              Try again
            </Button>
          ) : undefined
        }
      />
    );
  }

  if (rows.length === 0) {
    return (
      <EmptyState
        icon={emptyIcon}
        size="compact"
        title={emptyTitle}
        description={emptyDescription}
      />
    );
  }

  return (
    <div className={cn("overflow-x-auto rounded-md border", className)}>
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((column) => (
              <TableHead
                key={column.id}
                className={cn(
                  ALIGN[column.align ?? "left"],
                  column.hideBelow && HIDE_BELOW[column.hideBelow],
                  column.headClassName,
                )}
              >
                {column.header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={rowKey(row)}>
              {columns.map((column) => (
                <TableCell
                  key={column.id}
                  className={cn(
                    ALIGN[column.align ?? "left"],
                    column.hideBelow && HIDE_BELOW[column.hideBelow],
                    column.className,
                  )}
                >
                  {column.cell(row)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export { DataTable };
