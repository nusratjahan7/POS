"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, Plus, ShieldAlert, ShoppingCart } from "lucide-react";

import { PurchaseDetailDialog } from "@/app/(dashboard)/purchases/purchase-detail-dialog";
import { PurchaseFormDialog } from "@/app/(dashboard)/purchases/purchase-form-dialog";
import { Can, useCan } from "@/components/auth/can";
import { DataTable, type DataTableColumn } from "@/components/data-table/data-table";
import { DataTablePagination } from "@/components/data-table/data-table-pagination";
import { DataTableSearch } from "@/components/data-table/data-table-search";
import { SelectFilter } from "@/components/data-table/select-filter";
import { useDataTable } from "@/components/data-table/use-data-table";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import {
  purchasesApi,
  type Purchase,
  type PurchaseStatus,
  type PurchaseSummary,
} from "@/lib/api/purchases";
import { branchesApi } from "@/lib/api/rbac";
import { businessApi } from "@/lib/api/settings";
import { suppliersApi } from "@/lib/api/suppliers";
import { formatMoney } from "@/lib/format";

const ALL = "all";

const STATUS_OPTIONS = [
  { value: ALL, label: "All statuses" },
  { value: "draft", label: "Draft" },
  { value: "pending", label: "Pending" },
  { value: "received", label: "Received" },
  { value: "cancelled", label: "Cancelled" },
];

const STATUS_BADGE: Record<
  PurchaseStatus,
  { label: string; variant: React.ComponentProps<typeof Badge>["variant"] }
> = {
  draft: { label: "Draft", variant: "neutral" },
  pending: { label: "Pending", variant: "warning" },
  received: { label: "Received", variant: "success" },
  cancelled: { label: "Cancelled", variant: "outline" },
};

export function PurchasesClient() {
  const canView = useCan("purchases:view");
  const canCreate = useCan("purchases:create");
  const canReadSuppliers = useCan("suppliers:read");
  const canReadBranches = useCan("branches:read");
  const canReadBusiness = useCan("business:read");
  const queryClient = useQueryClient();

  const table = useDataTable();
  const [status, setStatus] = React.useState(ALL);
  const [supplierFilter, setSupplierFilter] = React.useState(ALL);
  const [branchFilter, setBranchFilter] = React.useState(ALL);

  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Purchase | null>(null);
  const [detailId, setDetailId] = React.useState<string | null>(null);

  const suppliersQuery = useQuery({
    queryKey: ["suppliers", "options"],
    queryFn: () => suppliersApi.options(),
    enabled: canReadSuppliers,
  });
  const branchesQuery = useQuery({
    queryKey: ["branches", "options"],
    queryFn: () => branchesApi.options(),
    enabled: canReadBranches,
  });
  const businessQuery = useQuery({
    queryKey: ["business"],
    queryFn: () => businessApi.get(),
    enabled: canReadBusiness,
  });

  const listQuery = useQuery({
    queryKey: ["purchases", { query: table.query, page: table.page, status, supplierFilter, branchFilter }],
    queryFn: () =>
      purchasesApi.list({
        search: table.query,
        page: table.page,
        status: status === ALL ? undefined : (status as PurchaseStatus),
        supplier_id: supplierFilter === ALL ? undefined : supplierFilter,
        branch_id: branchFilter === ALL ? undefined : branchFilter,
      }),
    enabled: canView,
  });

  const purchases = listQuery.data?.items ?? [];
  const currency = businessQuery.data?.currency ?? "USD";

  const supplierOptions = React.useMemo(
    () => [
      { value: ALL, label: "All suppliers" },
      ...(suppliersQuery.data ?? []).map((supplier) => ({ value: supplier.id, label: supplier.name })),
    ],
    [suppliersQuery.data],
  );

  const branchOptions = React.useMemo(
    () => [
      { value: ALL, label: "All branches" },
      ...(branchesQuery.data ?? []).map((branch) => ({ value: branch.id, label: branch.name })),
    ],
    [branchesQuery.data],
  );

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["purchases"] });
  }

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(purchase: Purchase) {
    setDetailId(null);
    setEditing(purchase);
    setFormOpen(true);
  }

  const columns: DataTableColumn<PurchaseSummary>[] = [
    {
      id: "number",
      header: "Purchase",
      cell: (purchase) => (
        <span className="font-mono text-xs">{purchase.purchase_number}</span>
      ),
    },
    {
      id: "supplier",
      header: "Supplier",
      cell: (purchase) => <span className="text-sm">{purchase.supplier.name}</span>,
    },
    {
      id: "branch",
      header: "Branch",
      hideBelow: "md",
      cell: (purchase) => <span className="text-sm">{purchase.branch.name}</span>,
    },
    {
      id: "date",
      header: "Date",
      hideBelow: "lg",
      cell: (purchase) => (
        <span className="text-muted-foreground text-sm tabular-nums">{purchase.purchase_date}</span>
      ),
    },
    {
      id: "total",
      header: "Total",
      align: "right",
      cell: (purchase) => (
        <span className="font-medium tabular-nums">{formatMoney(purchase.total, currency)}</span>
      ),
    },
    {
      id: "due",
      header: "Due",
      align: "right",
      hideBelow: "md",
      cell: (purchase) => (
        <span className="text-muted-foreground text-sm tabular-nums">
          {formatMoney(purchase.due, currency)}
        </span>
      ),
    },
    {
      id: "status",
      header: "Status",
      cell: (purchase) => (
        <Badge variant={STATUS_BADGE[purchase.status].variant}>
          {STATUS_BADGE[purchase.status].label}
        </Badge>
      ),
    },
    {
      id: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (purchase) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setDetailId(purchase.id)}
          aria-label={`View ${purchase.purchase_number}`}
        >
          <Eye className="size-4" />
          View
        </Button>
      ),
    },
  ];

  if (!canView) {
    return (
      <PageContainer>
        <PageHeader title="Purchases" description="Stock you have ordered and received." />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to purchases"
              description="This screen requires the purchases:view permission. Ask an administrator to grant you a role that includes it."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Purchases"
        description="Order stock from suppliers and receive it into a branch. Only receiving moves stock."
        actions={
          <Can permission="purchases:create">
            <Button onClick={openCreate}>
              <Plus className="size-4" />
              New purchase
            </Button>
          </Can>
        }
      />

      <Card>
        <CardHeader className="flex-col items-stretch gap-3 lg:flex-row lg:items-center">
          <div className="shrink-0">
            <CardTitle>All purchases</CardTitle>
            <CardDescription>
              {listQuery.data
                ? `${listQuery.data.total} purchase${listQuery.data.total === 1 ? "" : "s"}`
                : "Loading purchases"}
            </CardDescription>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:flex sm:min-w-0 sm:flex-nowrap sm:items-center sm:gap-3 sm:overflow-x-auto sm:pb-0.5">
            <DataTableSearch
              value={table.search}
              onValueChange={table.setSearch}
              placeholder="Search purchase number"
              ariaLabel="Search purchases"
              className="col-span-2"
            />
            <SelectFilter
              value={supplierFilter}
              onValueChange={(value) => {
                setSupplierFilter(value);
                table.resetPage();
              }}
              options={supplierOptions}
              ariaLabel="Filter by supplier"
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
              className="sm:w-44"
            />
            <SelectFilter
              value={status}
              onValueChange={(value) => {
                setStatus(value);
                table.resetPage();
              }}
              options={STATUS_OPTIONS}
              ariaLabel="Filter by status"
              className="sm:w-40"
            />
          </div>
        </CardHeader>

        <CardContent>
          <DataTable
            columns={columns}
            rows={purchases}
            rowKey={(purchase) => purchase.id}
            isLoading={listQuery.isPending}
            error={listQuery.error}
            onRetry={() => void listQuery.refetch()}
            emptyIcon={ShoppingCart}
            emptyTitle={table.query ? "No purchases match your filters" : "No purchases yet"}
            emptyDescription={
              table.query
                ? "Try a different purchase number or clear the filters."
                : canCreate
                  ? "Raise your first purchase order to stock a branch."
                  : "Purchases raised by your team will appear here."
            }
          />

          <DataTablePagination
            page={listQuery.data?.page ?? 1}
            pages={listQuery.data?.pages ?? 1}
            total={listQuery.data?.total}
            onPageChange={table.setPage}
          />
        </CardContent>
      </Card>

      {formOpen ? (
        <PurchaseFormDialog
          key={editing?.id ?? "new"}
          purchase={editing}
          onClose={() => setFormOpen(false)}
          onSaved={invalidate}
        />
      ) : null}

      {detailId ? (
        <PurchaseDetailDialog
          purchaseId={detailId}
          onClose={() => setDetailId(null)}
          onChanged={invalidate}
          onEdit={openEdit}
        />
      ) : null}
    </PageContainer>
  );
}
