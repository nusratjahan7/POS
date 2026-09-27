"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ImageIcon, Pencil, Plus, ShieldAlert, Tag, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { BrandFormDialog } from "@/app/(dashboard)/brands/brand-form-dialog";
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
import { describeError, mediaUrl } from "@/lib/api/client";
import { brandsApi, type Brand } from "@/lib/api/catalog";
import { formatDateTime } from "@/lib/format";

const ALL = "all";

const STATUS_OPTIONS = [
  { value: ALL, label: "All statuses" },
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
];

export function BrandsClient() {
  const canRead = useCan("catalog:read");
  const canWrite = useCan("catalog:write");
  const queryClient = useQueryClient();

  const table = useDataTable();
  const [status, setStatus] = React.useState(ALL);

  const listQuery = useQuery({
    queryKey: ["brands", { query: table.query, page: table.page, status }],
    queryFn: () =>
      brandsApi.list({
        search: table.query,
        page: table.page,
        is_active: status === ALL ? undefined : status === "active",
      }),
    enabled: canRead,
  });

  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Brand | null>(null);

  const brands = listQuery.data?.items ?? [];

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["brands"] });
  }

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(brand: Brand) {
    setEditing(brand);
    setFormOpen(true);
  }

  async function handleDelete(brand: Brand) {
    try {
      await brandsApi.remove(brand.id);
      toast.success(`Deleted ${brand.name}`);
      invalidate();
    } catch (cause) {
      toast.error(describeError(cause));
    }
  }

  const columns: DataTableColumn<Brand>[] = [
    {
      id: "brand",
      header: "Brand",
      cell: (brand) => (
        <div className="flex items-center gap-3">
          <div className="bg-muted flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-md border">
            {mediaUrl(brand.logo_url) ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={mediaUrl(brand.logo_url) as string}
                alt=""
                className="size-full object-contain p-0.5"
              />
            ) : (
              <ImageIcon className="text-muted-foreground size-4" aria-hidden />
            )}
          </div>
          <div className="flex min-w-0 flex-col">
            <span className="truncate font-medium">{brand.name}</span>
            <span className="text-muted-foreground truncate font-mono text-xs">{brand.slug}</span>
          </div>
        </div>
      ),
    },
    {
      id: "description",
      header: "Description",
      hideBelow: "md",
      cell: (brand) => (
        <span className="text-muted-foreground line-clamp-1 max-w-[28rem] text-sm">
          {brand.description || "—"}
        </span>
      ),
    },
    {
      id: "status",
      header: "Status",
      cell: (brand) => (
        <Badge variant={brand.is_active ? "success" : "outline"}>
          {brand.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      id: "updated",
      header: "Updated",
      hideBelow: "lg",
      cell: (brand) => (
        <span className="text-muted-foreground text-sm tabular-nums">
          {formatDateTime(brand.updated_at)}
        </span>
      ),
    },
    {
      id: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (brand) => (
        <div className="flex items-center justify-end gap-1">
          <Can permission="catalog:write">
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => openEdit(brand)}
              aria-label={`Edit ${brand.name}`}
            >
              <Pencil className="size-4" />
            </Button>
          </Can>
          <Can permission="catalog:delete">
            <ConfirmDialog
              title={`Delete ${brand.name}?`}
              description="It must have no products first. This cannot be undone."
              confirmLabel="Delete brand"
              onConfirm={() => handleDelete(brand)}
              trigger={
                <Button variant="ghost" size="icon-sm" aria-label={`Delete ${brand.name}`}>
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
        <PageHeader title="Brands" description="The manufacturers and labels you stock." />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to the catalogue"
              description="This screen requires the catalog:read permission. Ask an administrator to grant you a role that includes it."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Brands"
        description="The manufacturers and labels you stock. Attach a brand to a product to group and filter it."
        actions={
          <Can permission="catalog:write">
            <Button onClick={openCreate}>
              <Plus className="size-4" />
              New brand
            </Button>
          </Can>
        }
      />

      <Card>
        <CardHeader>
          <div>
            <CardTitle>All brands</CardTitle>
            <CardDescription>
              {listQuery.data
                ? `${listQuery.data.total} brand${listQuery.data.total === 1 ? "" : "s"}`
                : "Loading brands"}
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <DataTableSearch
              value={table.search}
              onValueChange={table.setSearch}
              placeholder="Search brands"
              ariaLabel="Search brands"
            />
            <SelectFilter
              value={status}
              onValueChange={(value) => {
                setStatus(value);
                table.resetPage();
              }}
              options={STATUS_OPTIONS}
              ariaLabel="Filter by status"
            />
          </div>
        </CardHeader>

        <CardContent>
          <DataTable
            columns={columns}
            rows={brands}
            rowKey={(brand) => brand.id}
            isLoading={listQuery.isPending}
            error={listQuery.error}
            onRetry={() => void listQuery.refetch()}
            emptyIcon={Tag}
            emptyTitle={table.query ? "No brands match your search" : "No brands yet"}
            emptyDescription={
              table.query
                ? "Try a different name."
                : "Create your first brand to start labelling products."
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
        <BrandFormDialog
          key={editing?.id ?? "new"}
          brand={editing}
          onClose={() => setFormOpen(false)}
          onSaved={invalidate}
        />
      ) : null}

      {!canWrite ? (
        <p className="text-muted-foreground text-xs">
          Your role can view brands but not change them.
        </p>
      ) : null}
    </PageContainer>
  );
}
