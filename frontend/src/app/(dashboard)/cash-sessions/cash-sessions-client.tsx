"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Calculator, Eye, ShieldAlert } from "lucide-react";

import { PickedDateRange, SalesDateRange } from "@/app/(dashboard)/sales/sales-date-range";
import { SessionDetailDialog } from "@/app/(dashboard)/cash-sessions/session-detail-dialog";
import { useCan } from "@/components/auth/can";
import { DataTable, type DataTableColumn } from "@/components/data-table/data-table";
import { DataTablePagination } from "@/components/data-table/data-table-pagination";
import { SelectFilter } from "@/components/data-table/select-filter";
import { useDataTable } from "@/components/data-table/use-data-table";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { registerSessionsApi, type RegisterSession } from "@/lib/api/register-sessions";
import { branchesApi } from "@/lib/api/rbac";
import { businessApi } from "@/lib/api/settings";
import { formatDateTime, formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";

const ALL = "all";

const STATUS_OPTIONS = [
  { value: ALL, label: "All sessions" },
  { value: "open", label: "Open" },
  { value: "closed", label: "Closed" },
];

function isoDay(value: PickedDateRange["start"] | undefined): string | undefined {
  return value ? value.toString().slice(0, 10) : undefined;
}

/** The register's shift history, expected vs counted, for oversight. */
export function CashSessionsClient() {
  const canRead = useCan("registers:read");

  const table = useDataTable();
  const [status, setStatus] = React.useState(ALL);
  const [branch, setBranch] = React.useState(ALL);
  const [range, setRange] = React.useState<PickedDateRange | null>(null);
  const [detailId, setDetailId] = React.useState<string | null>(null);

  const businessQuery = useQuery({ queryKey: ["business"], queryFn: () => businessApi.get() });
  const branchesQuery = useQuery({
    queryKey: ["branches", "options"],
    queryFn: () => branchesApi.options(),
    enabled: canRead,
  });

  const listQuery = useQuery({
    queryKey: ["register-sessions", { status, branch, page: table.page, from: isoDay(range?.start), to: isoDay(range?.end) }],
    queryFn: () =>
      registerSessionsApi.list({
        status: status === ALL ? undefined : (status as "open" | "closed"),
        branch_id: branch === ALL ? undefined : branch,
        date_from: isoDay(range?.start),
        date_to: isoDay(range?.end),
        page: table.page,
      }),
    enabled: canRead,
  });

  const sessions = listQuery.data?.items ?? [];
  const currency = businessQuery.data?.currency ?? "USD";

  const branchOptions = [
    { value: ALL, label: "All branches" },
    ...(branchesQuery.data ?? []).map((row) => ({ value: row.id, label: row.name })),
  ];

  const columns: DataTableColumn<RegisterSession>[] = [
    {
      id: "register",
      header: "Register",
      cell: (session) => (
        <div className="flex flex-col">
          <span className="font-medium">{session.register.name}</span>
          <span className="text-muted-foreground text-xs">{session.branch.name}</span>
        </div>
      ),
    },
    {
      id: "cashier",
      header: "Cashier",
      hideBelow: "md",
      cell: (session) => (
        <span className="text-sm">{session.opened_by?.full_name ?? "—"}</span>
      ),
    },
    {
      id: "opened",
      header: "Opened",
      hideBelow: "md",
      cell: (session) => (
        <span className="text-muted-foreground text-sm tabular-nums">
          {formatDateTime(session.opened_at)}
        </span>
      ),
    },
    {
      id: "status",
      header: "Status",
      cell: (session) => (
        <Badge variant={session.status === "open" ? "success" : "outline"}>
          {session.status === "open" ? "Open" : "Closed"}
        </Badge>
      ),
    },
    {
      id: "expected",
      header: "Expected",
      align: "right",
      hideBelow: "lg",
      cell: (session) => (
        <span className="tabular-nums">{formatMoney(session.expected_cash ?? "0", currency)}</span>
      ),
    },
    {
      id: "actual",
      header: "Counted",
      align: "right",
      hideBelow: "lg",
      cell: (session) => (
        <span className="tabular-nums">
          {session.actual_cash === null ? "—" : formatMoney(session.actual_cash, currency)}
        </span>
      ),
    },
    {
      id: "difference",
      header: "Difference",
      align: "right",
      cell: (session) => {
        if (session.actual_cash === null) return <span className="text-muted-foreground">—</span>;
        const difference = Number(session.difference ?? "0");
        return (
          <span
            className={cn(
              "font-medium tabular-nums",
              difference === 0 ? "text-success" : "text-destructive",
            )}
          >
            {formatMoney(difference, currency)}
          </span>
        );
      },
    },
    {
      id: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (session) => (
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => setDetailId(session.id)}
          aria-label="View session"
        >
          <Eye className="size-4" />
        </Button>
      ),
    },
  ];

  if (!canRead) {
    return (
      <PageContainer>
        <PageHeader title="Cash Sessions" description="Register shifts and their reconciliation." />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to cash sessions"
              description="This screen requires the registers:read permission. Ask an administrator to grant you a role that includes it."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Cash Sessions"
        description="Every register shift, what should have been in the drawer, and what was counted."
      />

      <Card>
        <CardHeader className="flex-col items-stretch gap-3 lg:flex-row lg:items-center">
          <div className="shrink-0">
            <CardTitle>Register sessions</CardTitle>
            <CardDescription>
              {listQuery.data
                ? `${listQuery.data.total} session${listQuery.data.total === 1 ? "" : "s"}`
                : "Loading sessions"}
            </CardDescription>
          </div>
          <div className="grid grid-cols-2 gap-3 lg:flex lg:min-w-0 lg:flex-nowrap lg:items-center lg:gap-3 lg:overflow-x-auto">
            <SalesDateRange value={range} onChange={setRange} />
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
            <SelectFilter
              value={branch}
              onValueChange={(value) => {
                setBranch(value);
                table.resetPage();
              }}
              options={branchOptions}
              ariaLabel="Filter by branch"
              className="sm:w-44"
            />
          </div>
        </CardHeader>

        <CardContent>
          <DataTable
            columns={columns}
            rows={sessions}
            rowKey={(session) => session.id}
            isLoading={listQuery.isPending}
            error={listQuery.error}
            onRetry={() => void listQuery.refetch()}
            emptyIcon={Calculator}
            emptyTitle="No register sessions"
            emptyDescription="Open a register at the till and its shift will appear here."
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
        <SessionDetailDialog sessionId={detailId} onClose={() => setDetailId(null)} />
      ) : null}
    </PageContainer>
  );
}
