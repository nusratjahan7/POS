"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ImageIcon, Package, Pencil, Plus, ShieldAlert, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { ProductFormDialog } from "@/app/(dashboard)/products/product-form-dialog";
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
import { brandsApi, categoriesApi } from "@/lib/api/catalog";
import { productsApi, type Product, type StockStatus } from "@/lib/api/products";
import { businessApi } from "@/lib/api/settings";
import { formatMoney } from "@/lib/format";

const ALL = "all";

const STATUS_OPTIONS = [
  { value: ALL, label: "All statuses" },
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
];

const SORT_OPTIONS = [
  { value: "name", label: "Name (A–Z)" },
  { value: "-name", label: "Name (Z–A)" },
  { value: "-created_at", label: "Newest first" },
  { value: "created_at", label: "Oldest first" },
  { value: "selling_price", label: "Price (low → high)" },
  { value: "-selling_price", label: "Price (high → low)" },
  { value: "stock_quantity", label: "Stock (low → high)" },
  { value: "-stock_quantity", label: "Stock (high → low)" },
];

type BadgeVariant = React.ComponentProps<typeof Badge>["variant"];

const STOCK_STATUS: Record<StockStatus, { label: string; variant: BadgeVariant }> = {
  in_stock: { label: "In stock", variant: "success" },
  low_stock: { label: "Low stock", variant: "warning" },
  out_of_stock: { label: "Out of stock", variant: "destructive" },
};

export function ProductsClient() {
  const canRead = useCan("catalog:read");
  const canWrite = useCan("catalog:write");
  const canReadBusiness = useCan("business:read");
  const queryClient = useQueryClient();

  const table = useDataTable();
  const [status, setStatus] = React.useState(ALL);
  const [category, setCategory] = React.useState(ALL);
  const [brand, setBrand] = React.useState(ALL);
  const [sort, setSort] = React.useState("name");

  const categoriesQuery = useQuery({
    queryKey: ["categories", "options"],
    queryFn: () => categoriesApi.options(),
    enabled: canRead,
  });
  const brandsQuery = useQuery({
    queryKey: ["brands", "options"],
    queryFn: () => brandsApi.options(),
    enabled: canRead,
  });
  const businessQuery = useQuery({
    queryKey: ["business"],
    queryFn: () => businessApi.get(),
    enabled: canReadBusiness,
  });

  const listQuery = useQuery({
    queryKey: ["products", { query: table.query, page: table.page, status, category, brand, sort }],
    queryFn: () =>
      productsApi.list({
        search: table.query,
        page: table.page,
        sort,
        is_active: status === ALL ? undefined : status === "active",
        category_id: category === ALL ? undefined : category,
        brand_id: brand === ALL ? undefined : brand,
      }),
    enabled: canRead,
  });

  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Product | null>(null);

  const products = listQuery.data?.items ?? [];
  const currency = businessQuery.data?.currency ?? "USD";

  const categoryOptions = React.useMemo(
    () => [
      { value: ALL, label: "All categories" },
      ...(categoriesQuery.data ?? []).map((item) => ({ value: item.id, label: item.name })),
    ],
    [categoriesQuery.data],
  );

  const brandOptions = React.useMemo(
    () => [
      { value: ALL, label: "All brands" },
      ...(brandsQuery.data ?? []).map((item) => ({ value: item.id, label: item.name })),
    ],
    [brandsQuery.data],
  );

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["products"] });
  }

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(product: Product) {
    setEditing(product);
    setFormOpen(true);
  }

  async function handleDelete(product: Product) {
    try {
      await productsApi.remove(product.id);
      toast.success(`Deleted ${product.name}`);
      invalidate();
    } catch (cause) {
      toast.error(describeError(cause));
    }
  }

  const columns: DataTableColumn<Product>[] = [
    {
      id: "product",
      header: "Product",
      cell: (product) => (
        <div className="flex items-center gap-3">
          <div className="bg-muted flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-md border">
            {mediaUrl(product.image_url) ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={mediaUrl(product.image_url) as string}
                alt=""
                className="size-full object-cover"
              />
            ) : (
              <ImageIcon className="text-muted-foreground size-4" aria-hidden />
            )}
          </div>
          <div className="flex min-w-0 flex-col">
            <span className="truncate font-medium">{product.name}</span>
            <span className="text-muted-foreground text-xs">{product.unit}</span>
          </div>
        </div>
      ),
    },
    {
      id: "sku",
      header: "SKU",
      cell: (product) => <span className="font-mono text-xs">{product.sku}</span>,
    },
    {
      id: "barcode",
      header: "Barcode",
      hideBelow: "lg",
      cell: (product) => (
        <span className="text-muted-foreground font-mono text-xs">{product.barcode ?? "—"}</span>
      ),
    },
    {
      id: "category",
      header: "Category",
      hideBelow: "md",
      cell: (product) => (
        <span className="text-sm">{product.category?.name ?? "—"}</span>
      ),
    },
    {
      id: "brand",
      header: "Brand",
      hideBelow: "lg",
      cell: (product) => <span className="text-sm">{product.brand?.name ?? "—"}</span>,
    },
    {
      id: "purchase_price",
      header: "Purchase",
      align: "right",
      hideBelow: "lg",
      cell: (product) => (
        <span className="text-muted-foreground text-sm tabular-nums">
          {formatMoney(product.purchase_price, currency)}
        </span>
      ),
    },
    {
      id: "selling_price",
      header: "Selling",
      align: "right",
      cell: (product) => (
        <span className="text-sm font-medium tabular-nums">
          {formatMoney(product.selling_price, currency)}
        </span>
      ),
    },
    {
      id: "stock",
      header: "Stock",
      cell: (product) => (
        <div className="flex flex-col gap-1">
          <Badge variant={STOCK_STATUS[product.stock_status].variant}>
            {STOCK_STATUS[product.stock_status].label}
          </Badge>
          <span className="text-muted-foreground text-xs tabular-nums">
            {product.stock_quantity} {product.unit}
          </span>
        </div>
      ),
    },
    {
      id: "status",
      header: "Status",
      cell: (product) => (
        <Badge variant={product.is_active ? "success" : "outline"}>
          {product.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      id: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (product) => (
        <div className="flex items-center justify-end gap-1">
          <Can permission="catalog:write">
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => openEdit(product)}
              aria-label={`Edit ${product.name}`}
            >
              <Pencil className="size-4" />
            </Button>
          </Can>
          <Can permission="catalog:delete">
            <ConfirmDialog
              title={`Delete ${product.name}?`}
              description="The product is hidden from the catalogue. Historical sales keep their reference."
              confirmLabel="Delete product"
              onConfirm={() => handleDelete(product)}
              trigger={
                <Button variant="ghost" size="icon-sm" aria-label={`Delete ${product.name}`}>
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
        <PageHeader title="Products" description="The items you sell." />
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
        title="Products"
        description="Everything you sell. Prices are stored as exact decimals; stock status is derived from the quantity and its minimum."
        actions={
          <Can permission="catalog:write">
            <Button onClick={openCreate}>
              <Plus className="size-4" />
              New product
            </Button>
          </Can>
        }
      />

      <Card>
        <CardHeader className="flex-col items-stretch gap-3 lg:flex-row lg:items-center">
          <div className="shrink-0">
            <CardTitle>All products</CardTitle>
            <CardDescription>
              {listQuery.data
                ? `${listQuery.data.total} product${listQuery.data.total === 1 ? "" : "s"}`
                : "Loading products"}
            </CardDescription>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:flex sm:min-w-0 sm:flex-nowrap sm:items-center sm:gap-3 sm:overflow-x-auto sm:pb-0.5">
            <DataTableSearch
              value={table.search}
              onValueChange={table.setSearch}
              placeholder="Search name, SKU or barcode"
              ariaLabel="Search products"
              className="col-span-2"
            />
            <SelectFilter
              value={category}
              onValueChange={(value) => {
                setCategory(value);
                table.resetPage();
              }}
              options={categoryOptions}
              ariaLabel="Filter by category"
              className="sm:w-52"
            />
            <SelectFilter
              value={brand}
              onValueChange={(value) => {
                setBrand(value);
                table.resetPage();
              }}
              options={brandOptions}
              ariaLabel="Filter by brand"
              className="sm:w-48"
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
            <SelectFilter
              value={sort}
              onValueChange={(value) => {
                setSort(value);
                table.resetPage();
              }}
              options={SORT_OPTIONS}
              ariaLabel="Sort products"
              className="sm:w-52"
            />
          </div>
        </CardHeader>

        <CardContent>
          <DataTable
            columns={columns}
            rows={products}
            rowKey={(product) => product.id}
            isLoading={listQuery.isPending}
            error={listQuery.error}
            onRetry={() => void listQuery.refetch()}
            emptyIcon={Package}
            emptyTitle={table.query ? "No products match your filters" : "No products yet"}
            emptyDescription={
              table.query
                ? "Try a different search term or clear the filters."
                : "Create your first product to start selling."
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
        <ProductFormDialog
          key={editing?.id ?? "new"}
          product={editing}
          onClose={() => setFormOpen(false)}
          onSaved={invalidate}
        />
      ) : null}

      {!canWrite ? (
        <p className="text-muted-foreground text-xs">
          Your role can view products but not change them.
        </p>
      ) : null}
    </PageContainer>
  );
}
