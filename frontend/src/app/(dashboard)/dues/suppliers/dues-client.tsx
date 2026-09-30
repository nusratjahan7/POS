"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, HandCoins, ShieldAlert } from "lucide-react";

import { Can, useCan } from "@/components/auth/can";
import { DataTable, type DataTableColumn } from "@/components/data-table/data-table";
import { DataTablePagination } from "@/components/data-table/data-table-pagination";
import { DataTableSearch } from "@/components/data-table/data-table-search";
import { SelectFilter } from "@/components/data-table/select-filter";
import { useDataTable } from "@/components/data-table/use-data-table";
import { LedgerDialog } from "@/components/dues/ledger-dialog";
import { SupplierPaymentDialog } from "@/components/dues/supplier-payment-dialog";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { businessApi } from "@/lib/api/settings";
import { suppliersApi, type Supplier } from "@/lib/api/suppliers";
import { formatMoney } from "@/lib/format";

const ALL = "all";

const STATUS_OPTIONS = [
  { value: ALL, label: "All statuses" },
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
];

const DUES_OPTIONS = [
  { value: "dues", label: "With outstanding balance" },
  { value: ALL, label: "All suppliers" },
];

/** Accounts payable: who you owe, and how much. */
export function SupplierDuesClient() {
  const canRead = useCan("suppliers:read");
  const canWrite = useCan("suppliers:write");
  const canReadBusiness = useCan("business:read");
  const queryClient = useQueryClient();

  const table = useDataTable();
  const [status, setStatus] = React.useState(ALL);
  const [dues, setDues] = React.useState("dues");

  const [paying, setPaying] = React.useState<Supplier | null>(null);
  const [ledger, setLedger] = React.useState<Supplier | null>(null);

  const businessQuery = useQuery({
    queryKey: ["business"],
    queryFn: () => businessApi.get(),
    enabled: canReadBusiness,
  });

  const listQuery = useQuery({
    queryKey: ["supplier-dues", { query: table.query, page: table.page, status, dues }],
    queryFn: () =>
      suppliersApi.list({
        search: table.query || undefined,
        page: table.page,
        is_active: status === ALL ? undefined : status === "active",
        has_dues: dues === "dues" ? true : undefined,
        sort: "-balance",
      }),
    enabled: canRead,
  });

  const suppliers = listQuery.data?.items ?? [];
  const currency = businessQuery.data?.currency ?? "USD";

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ["supplier-dues"] });
    void queryClient.invalidateQueries({ queryKey: ["suppliers"] });
    void queryClient.invalidateQueries({ queryKey: ["ledger"] });
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
      id: "balance",
      header: "Outstanding",
      align: "right",
      cell: (supplier) => (
        <span className="font-medium tabular-nums">{formatMoney(supplier.balance, currency)}</span>
      ),
    },
    {
      id: "status",
      header: "Status",
      hideBelow: "md",
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
              variant="secondary"
              size="sm"
              onClick={() => setPaying(supplier)}
              disabled={Number(supplier.balance) <= 0}
            >
              Record payment
            </Button>
          </Can>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setLedger(supplier)}
            aria-label={`View ${supplier.name}'s ledger`}
          >
            <BookOpen className="size-4" />
          </Button>
        </div>
      ),
    },
  ];

  if (!canRead) {
    return (
      <PageContainer>
        <PageHeader title="Supplier Dues" description="What you owe your suppliers." />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to supplier dues"
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
        title="Supplier Dues"
        description="Outstanding balances across your suppliers, with each account's ledger and payments."
      />

      <Card>
        <CardHeader className="flex-col items-stretch gap-3 sm:flex-row sm:items-center">
          <div className="shrink-0">
            <CardTitle>Accounts payable</CardTitle>
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
              value={dues}
              onValueChange={(value) => {
                setDues(value);
                table.resetPage();
              }}
              options={DUES_OPTIONS}
              ariaLabel="Filter by balance"
              className="sm:w-52"
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
            emptyIcon={HandCoins}
            emptyTitle={table.query ? "No suppliers match your search" : "No outstanding dues"}
            emptyDescription={
              table.query
                ? "Try a different name, company or phone."
                : "Every supplier account is settled."
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

      {!canWrite ? (
        <p className="text-muted-foreground text-xs">
          Your role can view dues but not record payments.
        </p>
      ) : null}

      {paying ? (
        <SupplierPaymentDialog
          supplier={paying}
          onClose={() => setPaying(null)}
          onPaid={refresh}
        />
      ) : null}

      {ledger ? (
        <LedgerDialog
          title={`${ledger.name} — account statement`}
          description="Every purchase, payment and opening balance on this supplier's account, with a running balance."
          cacheKey={`supplier:${ledger.id}`}
          fetchStatement={(params) => suppliersApi.ledger(ledger.id, params)}
          onClose={() => setLedger(null)}
        />
      ) : null}
    </PageContainer>
  );
}
