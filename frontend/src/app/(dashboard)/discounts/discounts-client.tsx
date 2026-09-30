"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgePercent, Pencil, Plus, ShieldAlert, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { DiscountFormDialog } from "@/app/(dashboard)/discounts/discount-form-dialog";
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
import { discountsApi, type Discount } from "@/lib/api/discounts";

const ALL = "all";

const SCOPE_OPTIONS = [
  { value: ALL, label: "All scopes" },
  { value: "cart", label: "Whole basket" },
  { value: "product", label: "Products" },
];

const KIND_OPTIONS = [
  { value: ALL, label: "All discounts" },
  { value: "coupons", label: "Coupons only" },
  { value: "automatic", label: "Automatic only" },
];

const STATUS_OPTIONS = [
  { value: ALL, label: "All statuses" },
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
];

export function DiscountsClient() {
  const canRead = useCan("discounts:read");
  const queryClient = useQueryClient();

  const table = useDataTable();
  const [scope, setScope] = React.useState(ALL);
  const [kind, setKind] = React.useState(ALL);
  const [status, setStatus] = React.useState(ALL);
  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Discount | null>(null);

  const listQuery = useQuery({
    queryKey: ["discounts", { query: table.query, page: table.page, scope, kind, status }],
    queryFn: () =>
      discountsApi.list({
        search: table.query || undefined,
        page: table.page,
        scope: scope === ALL ? undefined : (scope as "product" | "cart"),
        coupons_only: kind === "coupons" ? true : kind === "automatic" ? false : undefined,
        is_active: status === ALL ? undefined : status === "active",
      }),
    enabled: canRead,
  });

  const discounts = listQuery.data?.items ?? [];

  const removeMutation = useMutation({
    mutationFn: (discountId: string) => discountsApi.remove(discountId),
    onSuccess: () => {
      toast.success("Discount removed");
      void queryClient.invalidateQueries({ queryKey: ["discounts"] });
    },
    onError: (cause) => toast.error(describeError(cause)),
  });

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ["discounts"] });
  }

  const columns: DataTableColumn<Discount>[] = [
    {
      id: "name",
      header: "Discount",
      cell: (discount) => (
        <div className="flex flex-col">
          <span className="truncate font-medium">{discount.name}</span>
          <span className="text-muted-foreground text-xs">
            {discount.scope === "cart" ? "Whole basket" : "Products"}
          </span>
        </div>
      ),
    },
    {
      id: "code",
      header: "Code",
      cell: (discount) =>
        discount.code ? (
          <Badge variant="info" className="font-mono">
            {discount.code}
          </Badge>
        ) : (
          <span className="text-muted-foreground text-xs">Automatic</span>
        ),
    },
    {
      id: "value",
      header: "Value",
      align: "right",
      cell: (discount) => (
        <span className="font-medium tabular-nums">
          {discount.type === "percentage" ? `${discount.value}%` : `− ${discount.value}`}
        </span>
      ),
    },
    {
      id: "window",
      header: "Valid",
      hideBelow: "lg",
      cell: (discount) => (
        <span className="text-muted-foreground text-xs">
          {discount.starts_at ? discount.starts_at.slice(0, 10) : "always"}
          {" → "}
          {discount.expires_at ? discount.expires_at.slice(0, 10) : "no expiry"}
        </span>
      ),
    },
    {
      id: "usage",
      header: "Used",
      align: "right",
      hideBelow: "lg",
      cell: (discount) => (
        <span className="text-sm tabular-nums">
          {discount.redeemed_count}
          {discount.usage_limit != null ? ` / ${discount.usage_limit}` : ""}
        </span>
      ),
    },
    {
      id: "status",
      header: "Status",
      cell: (discount) => (
        <Badge variant={discount.is_active ? "success" : "outline"}>
          {discount.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      id: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (discount) => (
        <div className="flex items-center justify-end gap-1">
          <Can permission="discounts:write">
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={`Edit ${discount.name}`}
              onClick={() => {
                setEditing(discount);
                setFormOpen(true);
              }}
            >
              <Pencil className="size-4" />
            </Button>
            <ConfirmDialog
              title={`Delete ${discount.name}?`}
              description="An automatic discount stops applying; a coupon stops redeeming. Past sales keep their recorded discount."
              confirmLabel="Delete discount"
              onConfirm={() => removeMutation.mutateAsync(discount.id)}
              trigger={
                <Button variant="ghost" size="icon-sm" aria-label={`Delete ${discount.name}`}>
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
        <PageHeader title="Discounts" description="Promotions and coupons." />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to discounts"
              description="This screen requires the discounts:read permission. Ask an administrator to grant you a role that includes it."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Discounts"
        description="Automatic promotions and coupons. The server prices every sale — the till only previews."
        actions={
          <Can permission="discounts:write">
            <Button
              onClick={() => {
                setEditing(null);
                setFormOpen(true);
              }}
            >
              <Plus className="size-4" />
              New discount
            </Button>
          </Can>
        }
      />

      <Card>
        <CardHeader className="flex-col items-stretch gap-3 lg:flex-row lg:items-center">
          <div className="shrink-0">
            <CardTitle>All discounts</CardTitle>
            <CardDescription>
              {listQuery.data
                ? `${listQuery.data.total} discount${listQuery.data.total === 1 ? "" : "s"}`
                : "Loading discounts"}
            </CardDescription>
          </div>
          <div className="grid grid-cols-2 gap-3 lg:flex lg:min-w-0 lg:flex-nowrap lg:items-center lg:gap-3 lg:overflow-x-auto">
            <DataTableSearch
              value={table.search}
              onValueChange={table.setSearch}
              placeholder="Search name or code"
              ariaLabel="Search discounts"
              className="col-span-2"
            />
            <SelectFilter
              value={kind}
              onValueChange={(value) => {
                setKind(value);
                table.resetPage();
              }}
              options={KIND_OPTIONS}
              ariaLabel="Filter by kind"
              className="sm:w-44"
            />
            <SelectFilter
              value={scope}
              onValueChange={(value) => {
                setScope(value);
                table.resetPage();
              }}
              options={SCOPE_OPTIONS}
              ariaLabel="Filter by scope"
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
            rows={discounts}
            rowKey={(discount) => discount.id}
            isLoading={listQuery.isPending}
            error={listQuery.error}
            onRetry={() => void listQuery.refetch()}
            emptyIcon={BadgePercent}
            emptyTitle={table.query ? "No discounts match your search" : "No discounts yet"}
            emptyDescription={
              table.query
                ? "Try a different name or code."
                : "Create a promotion or a coupon to get started."
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
        <DiscountFormDialog
          key={editing?.id ?? "new"}
          discount={editing}
          onClose={() => setFormOpen(false)}
          onSaved={refresh}
        />
      ) : null}
    </PageContainer>
  );
}
