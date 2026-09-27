"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, ShieldAlert, Trash2, Truck } from "lucide-react";
import { toast } from "sonner";

import { SupplierFormDialog } from "@/app/(dashboard)/suppliers/supplier-form-dialog";
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
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { ErrorState } from "@/components/ui/error-state";
import { describeError } from "@/lib/api/client";
import { businessApi } from "@/lib/api/settings";
import { suppliersApi, type Supplier } from "@/lib/api/suppliers";
import { formatMoney } from "@/lib/format";

const ALL = "all";

const STATUS_OPTIONS = [
  { value: ALL, label: "All statuses" },
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
];

export function SuppliersClient() {
  const canRead = useCan("suppliers:read");
  const canWrite = useCan("suppliers:write");
  const canReadBusiness = useCan("business:read");
  const queryClient = useQueryClient();

  const table = useDataTable();
  const [status, setStatus] = React.useState(ALL);

  const businessQuery = useQuery({
    queryKey: ["business"],
    queryFn: () => businessApi.get(),
    enabled: canReadBusiness,
  });

  const listQuery = useQuery({
    queryKey: ["suppliers", { query: table.query, page: table.page, status }],
    queryFn: () =>
      suppliersApi.list({
        search: table.query,
        page: table.page,
        is_active: status === ALL ? undefined : status === "active",
      }),
    enabled: canRead,
  });

  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Supplier | null>(null);

  const suppliers = listQuery.data?.items ?? [];
  const currency = businessQuery.data?.currency ?? "USD";

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["suppliers"] });
  }

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(supplier: Supplier) {
    setEditing(supplier);
    setFormOpen(true);
  }

  async function handleDelete(supplier: Supplier) {
    try {
      await suppliersApi.remove(supplier.id);
      toast.success(`Deleted ${supplier.name}`);
      invalidate();
    } catch (cause) {
      toast.error(describeError(cause));
    }
  }

  const columns: DataTableColumn<Supplier>[] = [
    {
      id: "supplier",
      header: "Supplier",
      cell: (supplier) => (
        <div className="flex flex-col">
          <span className="truncate font-medium">{supplier.name}</span>
          {supplier.company ? (
            <span className="text-muted-foreground truncate text-xs">{supplier.company}</span>
          ) : null}
        </div>
      ),
    },
    {
      id: "contact",
      header: "Contact",
      hideBelow: "md",
      cell: (supplier) => (
        <div className="flex flex-col">
          <span className="text-sm">{supplier.phone ?? "—"}</span>
          {supplier.email ? (
            <span className="text-muted-foreground truncate text-xs">{supplier.email}</span>
          ) : null}
        </div>
      ),
    },
    {
      id: "opening_balance",
      header: "Opening",
      align: "right",
      hideBelow: "lg",
      cell: (supplier) => (
        <span className="text-muted-foreground text-sm tabular-nums">
          {formatMoney(supplier.opening_balance, currency)}
        </span>
      ),
    },
    {
      id: "balance",
      header: "Balance owed",
      align: "right",
      cell: (supplier) => (
        <span className="font-medium tabular-nums">{formatMoney(supplier.balance, currency)}</span>
      ),
    },
    {
      id: "status",
      header: "Status",
      cell: (supplier) => (
        <Badge variant={supplier.is_active ? "success" : "outline"}>
          {supplier.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      id: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (supplier) => (
        <div className="flex items-center justify-end gap-1">
          <Can permission="suppliers:write">
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => openEdit(supplier)}
              aria-label={`Edit ${supplier.name}`}
            >
              <Pencil className="size-4" />
            </Button>
            <ConfirmDialog
              title={`Delete ${supplier.name}?`}
              description="Suppliers with purchase history cannot be deleted — deactivate them instead."
              confirmLabel="Delete supplier"
              onConfirm={() => handleDelete(supplier)}
              trigger={
                <Button variant="ghost" size="icon-sm" aria-label={`Delete ${supplier.name}`}>
                  <Trash2 className="size-4" />
                </Button>
              }
            />
          </Can>
        </div>
      ),
    },
  ];

  if (!canRead) {
    return (
      <PageContainer>
        <PageHeader title="Suppliers" description="The vendors you buy stock from." />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to suppliers"
              description="This screen requires the suppliers:read permission. Ask an administrator to grant you a role that includes it."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Suppliers"
        description="The vendors you buy stock from, and the running balance you owe each one."
        actions={
          <Can permission="suppliers:write">
            <Button onClick={openCreate}>
              <Plus className="size-4" />
              New supplier
            </Button>
          </Can>
        }
      />

      <Card>
        <CardHeader className="flex-col items-stretch gap-3 sm:flex-row sm:items-center">
          <div className="shrink-0">
            <CardTitle>All suppliers</CardTitle>
            <CardDescription>
              {listQuery.data
                ? `${listQuery.data.total} supplier${listQuery.data.total === 1 ? "" : "s"}`
                : "Loading suppliers"}
            </CardDescription>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:flex sm:min-w-0 sm:flex-nowrap sm:items-center sm:gap-3 sm:overflow-x-auto sm:pb-0.5">
            <DataTableSearch
              value={table.search}
              onValueChange={table.setSearch}
              placeholder="Search name, company or phone"
              ariaLabel="Search suppliers"
              className="col-span-2"
            />
            <SelectFilter
              value={status}
              onValueChange={(value) => {
                setStatus(value);
                table.resetPage();
              }}
              options={STATUS_OPTIONS}
              ariaLabel="Filter by status"
              className="sm:w-44"
            />
          </div>
        </CardHeader>

        <CardContent>
          <DataTable
            columns={columns}
            rows={suppliers}
            rowKey={(supplier) => supplier.id}
            isLoading={listQuery.isPending}
            error={listQuery.error}
            onRetry={() => void listQuery.refetch()}
            emptyIcon={Truck}
            emptyTitle={table.query ? "No suppliers match your search" : "No suppliers yet"}
            emptyDescription={
              table.query
                ? "Try a different name, company or phone."
                : "Add your first supplier to start raising purchases."
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
        <SupplierFormDialog
          key={editing?.id ?? "new"}
          supplier={editing}
          onClose={() => setFormOpen(false)}
          onSaved={invalidate}
        />
      ) : null}

      {!canWrite ? (
        <p className="text-muted-foreground text-xs">
          Your role can view suppliers but not change them.
        </p>
      ) : null}
    </PageContainer>
  );
}
