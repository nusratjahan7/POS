"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeftRight, ArrowRight, Eye, Pencil, Plus, ShieldAlert } from "lucide-react";
import { toast } from "sonner";

import { SalesDateRange, type PickedDateRange } from "@/app/(dashboard)/sales/sales-date-range";
import { TransferDetailDialog } from "@/app/(dashboard)/transfers/transfer-detail-dialog";
import { TransferFormDialog } from "@/app/(dashboard)/transfers/transfer-form-dialog";
import { useAuth } from "@/components/auth/auth-provider";
import { Can, useCan } from "@/components/auth/can";
import { BranchFilter } from "@/components/branch/branch-filter";
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
import { describeError } from "@/lib/api/client";
import {
  transfersApi,
  type Transfer,
  type TransferStatus,
  type TransferSummary,
} from "@/lib/api/transfers";
import { ALL_BRANCHES, defaultBranchId } from "@/lib/auth/branches";
import { formatDateTime, formatQuantity } from "@/lib/format";
import { TRANSFER_STATUS_META } from "@/lib/transfers/status";

const ALL = "all";

const STATUS_OPTIONS = [
  { value: ALL, label: "All statuses" },
  { value: "draft", label: "Draft" },
  { value: "requested", label: "Requested" },
  { value: "approved", label: "Approved" },
  { value: "shipped", label: "Shipped" },
  { value: "received", label: "Received" },
  { value: "cancelled", label: "Cancelled" },
];

const SORT_OPTIONS = [
  { value: "-created_at", label: "Newest first" },
  { value: "created_at", label: "Oldest first" },
  { value: "transfer_number", label: "Transfer no." },
  { value: "-received_at", label: "Recently received" },
];

function isoDay(value: PickedDateRange["start"] | undefined): string | undefined {
  return value ? value.toString().slice(0, 10) : undefined;
}

export function TransfersClient() {
  const canRead = useCan("transfers:read");
  const canWrite = useCan("transfers:write");
  const { user } = useAuth();

  const table = useDataTable();
  const [status, setStatus] = React.useState(ALL);
  const [branch, setBranch] = React.useState(() => defaultBranchId(user));
  const [range, setRange] = React.useState<PickedDateRange | null>(null);
  const [sort, setSort] = React.useState("-created_at");
  const [detailId, setDetailId] = React.useState<string | null>(null);
  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Transfer | null>(null);

  const dateFrom = isoDay(range?.start);
  const dateTo = isoDay(range?.end);

  const listQuery = useQuery({
    queryKey: ["transfers", { query: table.query, page: table.page, status, branch, dateFrom, dateTo, sort }],
    queryFn: () =>
      transfersApi.list({
        search: table.query || undefined,
        page: table.page,
        status: status === ALL ? undefined : (status as TransferStatus),
        branch_id: branch === ALL_BRANCHES ? undefined : branch,
        date_from: dateFrom,
        date_to: dateTo,
        sort,
      }),
    enabled: canRead,
  });

  const transfers = listQuery.data?.items ?? [];

  async function openEdit(row: TransferSummary) {
    // The list row is a summary; load the full record for the form.
    try {
      setEditing(await transfersApi.get(row.id));
      setFormOpen(true);
    } catch (cause) {
      toast.error(describeError(cause));
    }
  }

  const columns: DataTableColumn<TransferSummary>[] = [
    {
      id: "transfer_number",
      header: "Transfer",
      cell: (row) => <span className="font-mono text-xs font-medium">{row.transfer_number}</span>,
    },
    {
      id: "status",
      header: "Status",
      cell: (row) => (
        <Badge variant={TRANSFER_STATUS_META[row.status].variant}>
          {TRANSFER_STATUS_META[row.status].label}
        </Badge>
      ),
    },
    {
      id: "route",
      header: "Route",
      cell: (row) => (
        <span className="flex items-center gap-1.5 text-sm">
          <span className="font-medium">{row.from_branch.name}</span>
          <ArrowRight className="text-muted-foreground size-3.5" aria-hidden />
          <span>{row.to_branch.name}</span>
        </span>
      ),
    },
    {
      id: "items",
      header: "Items",
      align: "right",
      hideBelow: "md",
      cell: (row) => (
        <span className="tabular-nums">
          {row.item_count} · {formatQuantity(row.total_quantity)}
        </span>
      ),
    },
    {
      id: "reference",
      header: "Reference",
      hideBelow: "lg",
      cell: (row) => (
        <span className="text-muted-foreground text-sm">{row.reference ?? "—"}</span>
      ),
    },
    {
      id: "created_at",
      header: "Created",
      hideBelow: "lg",
      cell: (row) => (
        <span className="text-muted-foreground text-sm tabular-nums">
          {formatDateTime(row.created_at)}
        </span>
      ),
    },
    {
      id: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (row) => (
        <div className="flex items-center justify-end gap-1">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setDetailId(row.id)}
            aria-label={`View ${row.transfer_number}`}
          >
            <Eye className="size-4" />
          </Button>
          {row.status === "draft" ? (
            <Can permission="transfers:write">
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => void openEdit(row)}
                aria-label={`Edit ${row.transfer_number}`}
              >
                <Pencil className="size-4" />
              </Button>
            </Can>
          ) : null}
        </div>
      ),
    },
  ];

  if (!canRead) {
    return (
      <PageContainer>
        <PageHeader title="Stock Transfers" description="Move stock between branches." />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to stock transfers"
              description="This screen requires the transfers:read permission. Ask an administrator to grant you a role that includes it."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Stock Transfers"
        description="Send stock between branches: raise, approve, ship, then receive. Stock moves at ship and receive only."
        actions={
          <Can permission="transfers:write">
            <Button
              onClick={() => {
                setEditing(null);
                setFormOpen(true);
              }}
            >
              <Plus className="size-4" />
              New transfer
            </Button>
          </Can>
        }
      />

      <Card>
        <CardHeader className="flex-col items-stretch gap-3 lg:flex-row lg:items-center">
          <div className="shrink-0">
            <CardTitle>All transfers</CardTitle>
            <CardDescription>
              {listQuery.data
                ? `${listQuery.data.total} transfer${listQuery.data.total === 1 ? "" : "s"}`
                : "Loading transfers"}
            </CardDescription>
          </div>
          <div className="grid grid-cols-2 gap-3 lg:flex lg:min-w-0 lg:flex-wrap lg:items-center">
            <DataTableSearch
              value={table.search}
              onValueChange={table.setSearch}
              placeholder="Search transfer number or reference"
              ariaLabel="Search transfers"
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
              className="sm:w-40"
            />
            <BranchFilter
              value={branch}
              onValueChange={(value) => {
                setBranch(value);
                table.resetPage();
              }}
              className="sm:w-48"
            />
            <SalesDateRange
              value={range}
              onChange={(next) => {
                setRange(next);
                table.resetPage();
              }}
            />
            <SelectFilter
              value={sort}
              onValueChange={(value) => {
                setSort(value);
                table.resetPage();
              }}
              options={SORT_OPTIONS}
              ariaLabel="Sort transfers"
              className="sm:w-48"
            />
          </div>
        </CardHeader>

        <CardContent>
          <DataTable
            columns={columns}
            rows={transfers}
            rowKey={(row) => row.id}
            isLoading={listQuery.isPending}
            error={listQuery.error}
            onRetry={() => void listQuery.refetch()}
            emptyIcon={ArrowLeftRight}
            emptyTitle={table.query ? "No transfers match your search" : "No transfers yet"}
            emptyDescription={
              table.query
                ? "Try a different transfer number or reference."
                : canWrite
                  ? "Raise a transfer to move stock between branches."
                  : "Transfers will appear here as they are raised."
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

      {detailId ? (
        <TransferDetailDialog
          transferId={detailId}
          onClose={() => setDetailId(null)}
          onChanged={() => void listQuery.refetch()}
        />
      ) : null}

      {formOpen ? (
        <TransferFormDialog
          key={editing?.id ?? "new"}
          transfer={editing}
          onClose={() => setFormOpen(false)}
          onSaved={() => void listQuery.refetch()}
        />
      ) : null}
    </PageContainer>
  );
}
