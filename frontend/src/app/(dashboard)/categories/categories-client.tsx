"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FolderTree, ImageIcon, Pencil, Plus, ShieldAlert, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { CategoryFormDialog } from "@/app/(dashboard)/categories/category-form-dialog";
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
import { categoriesApi, type Category, type CategoryNode } from "@/lib/api/catalog";
import { flattenCategoryTree } from "@/lib/catalog-tree";
import { formatDateTime } from "@/lib/format";

const ALL = "all";
const TOP_LEVEL = "top";

const STATUS_OPTIONS = [
  { value: ALL, label: "All statuses" },
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
];

function collectBranchIds(nodes: CategoryNode[]): Set<string> {
  const ids = new Set<string>();
  const walk = (list: CategoryNode[]) => {
    for (const node of list) {
      if (node.children.length > 0) ids.add(node.id);
      walk(node.children);
    }
  };
  walk(nodes);
  return ids;
}

export function CategoriesClient() {
  const canRead = useCan("catalog:read");
  const canWrite = useCan("catalog:write");
  const queryClient = useQueryClient();

  const table = useDataTable();
  const [status, setStatus] = React.useState(ALL);
  const [parent, setParent] = React.useState(ALL);

  const treeQuery = useQuery({
    queryKey: ["categories", "tree"],
    queryFn: () => categoriesApi.tree(),
    enabled: canRead,
  });

  const listQuery = useQuery({
    queryKey: ["categories", { query: table.query, page: table.page, status, parent }],
    queryFn: () =>
      categoriesApi.list({
        search: table.query,
        page: table.page,
        is_active: status === ALL ? undefined : status === "active",
        parent_id: parent === ALL || parent === TOP_LEVEL ? undefined : parent,
        top_level: parent === TOP_LEVEL ? true : undefined,
      }),
    enabled: canRead,
  });

  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Category | null>(null);

  const categories = listQuery.data?.items ?? [];
  const tree = React.useMemo(() => treeQuery.data ?? [], [treeQuery.data]);

  const parentFilterOptions = React.useMemo(
    () => [
      { value: ALL, label: "All categories" },
      { value: TOP_LEVEL, label: "Top level only" },
      ...flattenCategoryTree(tree).map((node) => ({
        value: node.id,
        label: `${"— ".repeat(node.depth)}${node.name}`,
      })),
    ],
    [tree],
  );

  const branchIds = React.useMemo(() => collectBranchIds(tree), [tree]);

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["categories"] });
  }

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(category: Category) {
    setEditing(category);
    setFormOpen(true);
  }

  async function handleDelete(category: Category) {
    try {
      await categoriesApi.remove(category.id);
      toast.success(`Deleted ${category.name}`);
      invalidate();
    } catch (cause) {
      toast.error(describeError(cause));
    }
  }

  const columns: DataTableColumn<Category>[] = [
    {
      id: "category",
      header: "Category",
      cell: (category) => (
        <div className="flex items-center gap-3">
          <div className="bg-muted flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-md border">
            {mediaUrl(category.image_url) ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={mediaUrl(category.image_url) as string}
                alt=""
                className="size-full object-cover"
              />
            ) : (
              <ImageIcon className="text-muted-foreground size-4" aria-hidden />
            )}
          </div>
          <div className="flex min-w-0 flex-col">
            <span className="flex items-center gap-1.5 font-medium">
              <span className="truncate">{category.name}</span>
              {branchIds.has(category.id) ? (
                <FolderTree
                  className="text-muted-foreground size-3.5 shrink-0"
                  aria-label="Has sub-categories"
                />
              ) : null}
            </span>
            <span className="text-muted-foreground truncate font-mono text-xs">
              {category.slug}
            </span>
          </div>
        </div>
      ),
    },
    {
      id: "parent",
      header: "Parent",
      cell: (category) =>
        category.parent ? (
          <span className="text-sm">{category.parent.name}</span>
        ) : (
          <span className="text-muted-foreground text-xs">Top level</span>
        ),
    },
    {
      id: "status",
      header: "Status",
      cell: (category) => (
        <Badge variant={category.is_active ? "success" : "outline"}>
          {category.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      id: "updated",
      header: "Updated",
      hideBelow: "md",
      cell: (category) => (
        <span className="text-muted-foreground text-sm tabular-nums">
          {formatDateTime(category.updated_at)}
        </span>
      ),
    },
    {
      id: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (category) => (
        <div className="flex items-center justify-end gap-1">
          <Can permission="catalog:write">
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => openEdit(category)}
              aria-label={`Edit ${category.name}`}
            >
              <Pencil className="size-4" />
            </Button>
          </Can>
          <Can permission="catalog:delete">
            <ConfirmDialog
              title={`Delete ${category.name}?`}
              description="It must have no sub-categories or products first. This cannot be undone."
              confirmLabel="Delete category"
              onConfirm={() => handleDelete(category)}
              trigger={
                <Button variant="ghost" size="icon-sm" aria-label={`Delete ${category.name}`}>
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
        <PageHeader title="Categories" description="Group products for browsing and reporting." />
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
        title="Categories"
        description="Group products into a hierarchy. Sub-categories let you report at a parent level."
        actions={
          <Can permission="catalog:write">
            <Button onClick={openCreate}>
              <Plus className="size-4" />
              New category
            </Button>
          </Can>
        }
      />

      <Card>
        <CardHeader className="flex-col items-stretch gap-3 sm:flex-row sm:items-center">
          <div className="shrink-0">
            <CardTitle>All categories</CardTitle>
            <CardDescription>
              {listQuery.data
                ? `${listQuery.data.total} categor${listQuery.data.total === 1 ? "y" : "ies"}`
                : "Loading categories"}
            </CardDescription>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:flex sm:min-w-0 sm:flex-nowrap sm:items-center sm:gap-3 sm:overflow-x-auto sm:pb-0.5">
            <DataTableSearch
              value={table.search}
              onValueChange={table.setSearch}
              placeholder="Search name or slug"
              ariaLabel="Search categories"
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
            />
            <SelectFilter
              value={parent}
              onValueChange={(value) => {
                setParent(value);
                table.resetPage();
              }}
              options={parentFilterOptions}
              ariaLabel="Filter by parent"
              className="sm:w-56"
            />
          </div>
        </CardHeader>

        <CardContent>
          <DataTable
            columns={columns}
            rows={categories}
            rowKey={(category) => category.id}
            isLoading={listQuery.isPending}
            error={listQuery.error}
            onRetry={() => void listQuery.refetch()}
            emptyIcon={FolderTree}
            emptyTitle={table.query ? "No categories match your filters" : "No categories yet"}
            emptyDescription={
              table.query
                ? "Try a different search term or clear the filters."
                : "Create your first category to organise the catalogue."
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
        <CategoryFormDialog
          key={editing?.id ?? "new"}
          category={editing}
          onClose={() => setFormOpen(false)}
          onSaved={invalidate}
        />
      ) : null}

      {!canWrite ? (
        <p className="text-muted-foreground text-xs">
          Your role can view categories but not change them.
        </p>
      ) : null}
    </PageContainer>
  );
}
