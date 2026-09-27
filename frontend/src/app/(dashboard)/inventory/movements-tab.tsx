"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { History } from "lucide-react";

import { useCan } from "@/components/auth/can";
import { DataTable, type DataTableColumn } from "@/components/data-table/data-table";
import { DataTablePagination } from "@/components/data-table/data-table-pagination";
import { DataTableSearch } from "@/components/data-table/data-table-search";
import { SelectFilter } from "@/components/data-table/select-filter";
import { useDataTable } from "@/components/data-table/use-data-table";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { inventoryApi, type Movement, type MovementType } from "@/lib/api/inventory";
import { branchesApi } from "@/lib/api/rbac";
import { formatDateTime, formatQuantity } from "@/lib/format";
import { cn } from "@/lib/utils";

const ALL = "all";

type BadgeVariant = React.ComponentProps<typeof Badge>["variant"];

const TYPE_META: Record<MovementType, { label: string; variant: BadgeVariant }> = {
  opening: { label: "Opening", variant: "info" },
  stock_in: { label: "Stock in", variant: "success" },
  stock_out: { label: "Stock out", variant: "warning" },
  adjustment: { label: "Adjustment", variant: "neutral" },
  damage: { label: "Damage", variant: "destructive" },
};

const TYPE_OPTIONS = [
  { value: ALL, label: "All movements" },
  { value: "stock_in", label: "Stock in" },
  { value: "stock_out", label: "Stock out" },
  { value: "adjustment", label: "Adjustment" },
  { value: "damage", label: "Damage" },
  { value: "opening", label: "Opening" },
];

export function MovementsTab() {
  const canReadBranches = useCan("branches:read");
  const table = useDataTable();
  const [branchFilter, setBranchFilter] = React.useState(ALL);
  const [typeFilter, setTypeFilter] = React.useState(ALL);

  const branchesQuery = useQuery({
    queryKey: ["branches", "options"],
    queryFn: () => branchesApi.options(),
    enabled: canReadBranches,
  });

  const movementsQuery = useQuery({
    queryKey: ["inventory", "movements", { query: table.query, page: table.page, branchFilter, typeFilter }],
    queryFn: () =>
      inventoryApi.listMovements({
        search: table.query,
        page: table.page,
        branch_id: branchFilter === ALL ? undefined : branchFilter,
        movement_type: typeFilter === ALL ? undefined : (typeFilter as MovementType),
      }),
  });

  const movements = movementsQuery.data?.items ?? [];

  const branchOptions = React.useMemo(
    () => [
      { value: ALL, label: "All branches" },
      ...(branchesQuery.data ?? []).map((branch) => ({ value: branch.id, label: branch.name })),
    ],
    [branchesQuery.data],
  );

  const columns: DataTableColumn<Movement>[] = [
    {
      id: "created_at",
      header: "When",
      cell: (movement) => (
        <span className="text-muted-foreground text-sm tabular-nums">
          {formatDateTime(movement.created_at)}
        </span>
      ),
    },
    {
      id: "product",
      header: "Product",
      cell: (movement) => (
        <div className="flex min-w-0 flex-col">
          <span className="truncate font-medium">{movement.product.name}</span>
          <span className="text-muted-foreground font-mono text-xs">{movement.product.sku}</span>
        </div>
      ),
    },
    {
      id: "branch",
      header: "Branch",
      hideBelow: "lg",
      cell: (movement) => <span className="text-sm">{movement.branch.name}</span>,
    },
    {
      id: "type",
      header: "Movement",
      cell: (movement) => (
        <Badge variant={TYPE_META[movement.movement_type].variant}>
          {TYPE_META[movement.movement_type].label}
        </Badge>
      ),
    },
    {
      id: "change",
      header: "Change",
      align: "right",
      cell: (movement) => {
        const positive = movement.quantity.startsWith("-") === false;
        return (
          <span
            className={cn(
              "font-medium tabular-nums",
              positive ? "text-success" : "text-destructive",
            )}
          >
            {positive ? "+" : ""}
            {formatQuantity(movement.quantity)}
          </span>
        );
      },
    },
    {
      id: "stock",
      header: "On hand",
      align: "right",
      cell: (movement) => (
        <span className="text-muted-foreground text-sm tabular-nums">
          {formatQuantity(movement.previous_stock)} →{" "}
          <span className="text-foreground">{formatQuantity(movement.new_stock)}</span>
        </span>
      ),
    },
    {
      id: "user",
      header: "By",
      hideBelow: "lg",
      cell: (movement) => (
        <span className="text-sm">{movement.user?.full_name ?? "System"}</span>
      ),
    },
    {
      id: "note",
      header: "Note",
      hideBelow: "lg",
      cell: (movement) => (
        <span className="text-muted-foreground line-clamp-1 max-w-[16rem] text-sm">
          {movement.note ?? "—"}
        </span>
      ),
    },
  ];

  return (
    <Card>
      <CardHeader className="flex-col items-stretch gap-3 lg:flex-row lg:items-center">
        <div className="shrink-0">
          <CardTitle>Movement history</CardTitle>
          <CardDescription>
            {movementsQuery.data
              ? `${movementsQuery.data.total} movement${movementsQuery.data.total === 1 ? "" : "s"}`
              : "Loading movements"}
          </CardDescription>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:flex sm:min-w-0 sm:flex-nowrap sm:items-center sm:gap-3 sm:overflow-x-auto sm:pb-0.5">
          <DataTableSearch
            value={table.search}
            onValueChange={table.setSearch}
            placeholder="Search name, SKU or barcode"
            ariaLabel="Search movements"
            className="col-span-2"
          />
          <SelectFilter
            value={typeFilter}
            onValueChange={(value) => {
              setTypeFilter(value);
              table.resetPage();
            }}
            options={TYPE_OPTIONS}
            ariaLabel="Filter by movement type"
            className="sm:w-48"
          />
          <SelectFilter
            value={branchFilter}
            onValueChange={(value) => {
              setBranchFilter(value);
              table.resetPage();
            }}
            options={branchOptions}
            ariaLabel="Filter by branch"
            className="sm:w-48"
          />
        </div>
      </CardHeader>

      <CardContent>
        <DataTable
          columns={columns}
          rows={movements}
          rowKey={(movement) => movement.id}
          isLoading={movementsQuery.isPending}
          error={movementsQuery.error}
          onRetry={() => void movementsQuery.refetch()}
          emptyIcon={History}
          emptyTitle={table.query ? "No movements match your filters" : "No stock movements yet"}
          emptyDescription={
            table.query
              ? "Try a different search term or clear the filters."
              : "Movements appear here as stock is received, sold or adjusted."
          }
        />

        <DataTablePagination
          page={movementsQuery.data?.page ?? 1}
          pages={movementsQuery.data?.pages ?? 1}
          total={movementsQuery.data?.total}
          onPageChange={table.setPage}
        />
      </CardContent>
    </Card>
  );
}
