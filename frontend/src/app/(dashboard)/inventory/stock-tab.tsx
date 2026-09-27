"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ImageIcon, PackageOpen, Plus, SlidersHorizontal } from "lucide-react";

import {
  StockAdjustmentDialog,
  type AdjustmentPreset,
} from "@/app/(dashboard)/inventory/stock-adjustment-dialog";
import { Can, useCan } from "@/components/auth/can";
import { DataTable, type DataTableColumn } from "@/components/data-table/data-table";
import { DataTablePagination } from "@/components/data-table/data-table-pagination";
import { DataTableSearch } from "@/components/data-table/data-table-search";
import { SelectFilter } from "@/components/data-table/select-filter";
import { useDataTable } from "@/components/data-table/use-data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { mediaUrl } from "@/lib/api/client";
import { categoriesApi } from "@/lib/api/catalog";
import { inventoryApi, type StockLevel, type StockStatus } from "@/lib/api/inventory";
import { productsApi } from "@/lib/api/products";
import { branchesApi } from "@/lib/api/rbac";
import { formatDateTime, formatQuantity } from "@/lib/format";
import { cn } from "@/lib/utils";

const ALL = "all";

type BadgeVariant = React.ComponentProps<typeof Badge>["variant"];

const STATUS_BADGE: Record<StockStatus, { label: string; variant: BadgeVariant }> = {
  in_stock: { label: "In stock", variant: "success" },
  low_stock: { label: "Low stock", variant: "warning" },
  out_of_stock: { label: "Out of stock", variant: "destructive" },
};

const STATUS_OPTIONS = [
  { value: ALL, label: "All stock" },
  { value: "in_stock", label: "In stock" },
  { value: "low_stock", label: "Low stock" },
  { value: "out_of_stock", label: "Out of stock" },
];

const SORT_OPTIONS = [
  { value: "product_name", label: "Name (A–Z)" },
  { value: "-product_name", label: "Name (Z–A)" },
  { value: "quantity", label: "Quantity (low → high)" },
  { value: "-quantity", label: "Quantity (high → low)" },
  { value: "-updated_at", label: "Recently changed" },
];

export function StockTab() {
  const canAdjust = useCan("inventory:adjust");
  const canReadCatalog = useCan("catalog:read");
  const canReadBranches = useCan("branches:read");
  const queryClient = useQueryClient();

  const table = useDataTable();
  const [branchFilter, setBranchFilter] = React.useState(ALL);
  const [categoryFilter, setCategoryFilter] = React.useState(ALL);
  const [status, setStatus] = React.useState(ALL);
  const [sort, setSort] = React.useState("product_name");

  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [preset, setPreset] = React.useState<AdjustmentPreset | undefined>(undefined);

  const branchesQuery = useQuery({
    queryKey: ["branches", "options"],
    queryFn: () => branchesApi.options(),
    enabled: canReadBranches,
  });
  const categoriesQuery = useQuery({
    queryKey: ["categories", "options"],
    queryFn: () => categoriesApi.options(),
    enabled: canReadCatalog,
  });
  const productsQuery = useQuery({
    queryKey: ["products", "options"],
    queryFn: () => productsApi.options(),
    enabled: canReadCatalog && canAdjust,
  });

  const branchParam = branchFilter === ALL ? undefined : branchFilter;

  const summaryQuery = useQuery({
    queryKey: ["inventory", "summary", branchParam],
    queryFn: () => inventoryApi.summary(branchParam),
  });

  const stockQuery = useQuery({
    queryKey: ["inventory", "stock", { query: table.query, page: table.page, branchFilter, categoryFilter, status, sort }],
    queryFn: () =>
      inventoryApi.listStock({
        search: table.query,
        page: table.page,
        sort,
        branch_id: branchParam,
        category_id: categoryFilter === ALL ? undefined : categoryFilter,
        status: status === ALL ? undefined : (status as StockStatus),
      }),
  });

  const levels = stockQuery.data?.items ?? [];

  const branchOptions = React.useMemo(
    () => [
      { value: ALL, label: "All branches" },
      ...(branchesQuery.data ?? []).map((branch) => ({ value: branch.id, label: branch.name })),
    ],
    [branchesQuery.data],
  );

  const categoryOptions = React.useMemo(
    () => [
      { value: ALL, label: "All categories" },
      ...(categoriesQuery.data ?? []).map((category) => ({
        value: category.id,
        label: category.name,
      })),
    ],
    [categoriesQuery.data],
  );

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["inventory"] });
    // The product's aggregate stock changed too.
    void queryClient.invalidateQueries({ queryKey: ["products"] });
  }

  function openAdjust(level: StockLevel) {
    setPreset({
      product: level.product,
      branch: level.branch,
      quantity: level.quantity,
    });
    setDialogOpen(true);
  }

  function openGeneral() {
    setPreset(undefined);
    setDialogOpen(true);
  }

  function applyStatus(next: string) {
    setStatus(next);
    table.resetPage();
  }

  const summary = summaryQuery.data;

  const columns: DataTableColumn<StockLevel>[] = [
    {
      id: "product",
      header: "Product",
      cell: (level) => (
        <div className="flex items-center gap-3">
          <div className="bg-muted flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-md border">
            {mediaUrl(level.product.image_url) ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={mediaUrl(level.product.image_url) as string}
                alt=""
                className="size-full object-cover"
              />
            ) : (
              <ImageIcon className="text-muted-foreground size-4" aria-hidden />
            )}
          </div>
          <div className="flex min-w-0 flex-col">
            <span className="truncate font-medium">{level.product.name}</span>
            <span className="text-muted-foreground font-mono text-xs">{level.product.sku}</span>
          </div>
        </div>
      ),
    },
    {
      id: "branch",
      header: "Branch",
      hideBelow: "md",
      cell: (level) => (
        <div className="flex flex-col">
          <span className="text-sm">{level.branch.name}</span>
          <span className="text-muted-foreground font-mono text-xs">{level.branch.code}</span>
        </div>
      ),
    },
    {
      id: "quantity",
      header: "On hand",
      align: "right",
      cell: (level) => (
        <span className="font-medium tabular-nums">{formatQuantity(level.quantity)}</span>
      ),
    },
    {
      id: "minimum",
      header: "Minimum",
      align: "right",
      hideBelow: "lg",
      cell: (level) => (
        <span className="text-muted-foreground text-sm tabular-nums">
          {formatQuantity(level.product.minimum_stock)}
        </span>
      ),
    },
    {
      id: "status",
      header: "Status",
      cell: (level) => (
        <Badge variant={STATUS_BADGE[level.stock_status].variant}>
          {STATUS_BADGE[level.stock_status].label}
        </Badge>
      ),
    },
    {
      id: "updated",
      header: "Updated",
      hideBelow: "lg",
      cell: (level) => (
        <span className="text-muted-foreground text-sm tabular-nums">
          {formatDateTime(level.updated_at)}
        </span>
      ),
    },
    {
      id: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (level) => (
        <Can permission="inventory:adjust">
          <Button variant="outline" size="sm" onClick={() => openAdjust(level)}>
            <SlidersHorizontal className="size-3.5" />
            Adjust
          </Button>
        </Can>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      {summary ? (
        <div className="grid gap-3 sm:grid-cols-3">
          {(
            [
              { key: "in_stock", label: "In stock", tone: "text-success" },
              { key: "low_stock", label: "Low stock", tone: "text-warning" },
              { key: "out_of_stock", label: "Out of stock", tone: "text-destructive" },
            ] as const
          ).map((card) => (
            <button
              key={card.key}
              type="button"
              onClick={() => applyStatus(status === card.key ? ALL : card.key)}
              className={cn(
                "bg-card hover:border-ring/60 focus-visible:ring-ring/60 rounded-lg border p-3 text-left transition-colors outline-none focus-visible:ring-2",
                status === card.key && "border-ring",
              )}
            >
              <div className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
                {card.label}
              </div>
              <div className={cn("mt-1 text-2xl font-semibold tabular-nums", card.tone)}>
                {summary[card.key]}
              </div>
            </button>
          ))}
        </div>
      ) : null}

      <Card>
        <CardHeader className="flex-col items-stretch gap-3 lg:flex-row lg:items-center">
          <div className="shrink-0">
            <CardTitle>Stock on hand</CardTitle>
            <CardDescription>
              {stockQuery.data
                ? `${stockQuery.data.total} tracked item${stockQuery.data.total === 1 ? "" : "s"}`
                : "Loading stock"}
            </CardDescription>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:flex sm:min-w-0 sm:flex-nowrap sm:items-center sm:gap-3 sm:overflow-x-auto sm:pb-0.5">
            <DataTableSearch
              value={table.search}
              onValueChange={table.setSearch}
              placeholder="Search name, SKU or barcode"
              ariaLabel="Search stock"
              className="col-span-2"
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
            <SelectFilter
              value={categoryFilter}
              onValueChange={(value) => {
                setCategoryFilter(value);
                table.resetPage();
              }}
              options={categoryOptions}
              ariaLabel="Filter by category"
              className="sm:w-48"
            />
            <SelectFilter
              value={status}
              onValueChange={applyStatus}
              options={STATUS_OPTIONS}
              ariaLabel="Filter by status"
              className="sm:w-44"
            />
            <SelectFilter
              value={sort}
              onValueChange={(value) => {
                setSort(value);
                table.resetPage();
              }}
              options={SORT_OPTIONS}
              ariaLabel="Sort stock"
              className="col-span-2 sm:w-52"
            />
            {canAdjust ? (
              <Button onClick={openGeneral} className="col-span-2 sm:col-span-1">
                <Plus className="size-4" />
                New adjustment
              </Button>
            ) : null}
          </div>
        </CardHeader>

        <CardContent>
          <DataTable
            columns={columns}
            rows={levels}
            rowKey={(level) => level.id}
            isLoading={stockQuery.isPending}
            error={stockQuery.error}
            onRetry={() => void stockQuery.refetch()}
            emptyIcon={PackageOpen}
            emptyTitle={table.query ? "No stock matches your filters" : "Nothing tracked yet"}
            emptyDescription={
              table.query
                ? "Try a different search term or clear the filters."
                : "Create a product to start tracking stock."
            }
          />

          <DataTablePagination
            page={stockQuery.data?.page ?? 1}
            pages={stockQuery.data?.pages ?? 1}
            total={stockQuery.data?.total}
            onPageChange={table.setPage}
          />
        </CardContent>
      </Card>

      {dialogOpen ? (
        <StockAdjustmentDialog
          key={preset ? `${preset.product.id}:${preset.branch.id}` : "general"}
          preset={preset}
          products={productsQuery.data ?? []}
          branches={branchesQuery.data ?? []}
          onClose={() => setDialogOpen(false)}
          onSaved={invalidate}
        />
      ) : null}
    </div>
  );
}
