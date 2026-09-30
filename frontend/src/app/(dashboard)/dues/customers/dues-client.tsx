"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, ShieldAlert, Wallet } from "lucide-react";

import { CustomerPaymentDialog } from "@/app/(dashboard)/customers/customer-payment-dialog";
import { Can, useCan } from "@/components/auth/can";
import { DataTable, type DataTableColumn } from "@/components/data-table/data-table";
import { DataTablePagination } from "@/components/data-table/data-table-pagination";
import { DataTableSearch } from "@/components/data-table/data-table-search";
import { SelectFilter } from "@/components/data-table/select-filter";
import { useDataTable } from "@/components/data-table/use-data-table";
import { LedgerDialog } from "@/components/dues/ledger-dialog";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { customersApi, type Customer } from "@/lib/api/customers";
import { businessApi } from "@/lib/api/settings";
import { formatMoney } from "@/lib/format";

const ALL = "all";

const STATUS_OPTIONS = [
  { value: ALL, label: "All statuses" },
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
];

const DUES_OPTIONS = [
  { value: "dues", label: "With outstanding balance" },
  { value: ALL, label: "All customers" },
];

/** Accounts receivable: who owes you, and how much. */
export function CustomerDuesClient() {
  const canRead = useCan("customers:read");
  const canWrite = useCan("customers:write");
  const canReadBusiness = useCan("business:read");
  const queryClient = useQueryClient();

  const table = useDataTable();
  const [status, setStatus] = React.useState(ALL);
  const [dues, setDues] = React.useState("dues");

  const [paying, setPaying] = React.useState<Customer | null>(null);
  const [ledger, setLedger] = React.useState<Customer | null>(null);

  const businessQuery = useQuery({
    queryKey: ["business"],
    queryFn: () => businessApi.get(),
    enabled: canReadBusiness,
  });

  const listQuery = useQuery({
    queryKey: ["customer-dues", { query: table.query, page: table.page, status, dues }],
    queryFn: () =>
      customersApi.list({
        search: table.query || undefined,
        page: table.page,
        is_active: status === ALL ? undefined : status === "active",
        has_dues: dues === "dues" ? true : undefined,
        sort: "-balance",
      }),
    enabled: canRead,
  });

  const customers = listQuery.data?.items ?? [];
  const currency = businessQuery.data?.currency ?? "USD";

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ["customer-dues"] });
    void queryClient.invalidateQueries({ queryKey: ["customers"] });
    void queryClient.invalidateQueries({ queryKey: ["ledger"] });
  }

  const columns: DataTableColumn<Customer>[] = [
    {
      id: "customer",
      header: "Customer",
      cell: (customer) => (
        <div className="flex flex-col">
          <span className="truncate font-medium">{customer.name}</span>
          {customer.phone ? (
            <span className="text-muted-foreground truncate text-xs">{customer.phone}</span>
          ) : null}
        </div>
      ),
    },
    {
      id: "balance",
      header: "Outstanding",
      align: "right",
      cell: (customer) => (
        <span className="font-medium tabular-nums">{formatMoney(customer.balance, currency)}</span>
      ),
    },
    {
      id: "status",
      header: "Status",
      hideBelow: "md",
      cell: (customer) => (
        <Badge variant={customer.is_active ? "success" : "outline"}>
          {customer.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      id: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (customer) => (
        <div className="flex items-center justify-end gap-1">
          <Can permission="customers:write">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPaying(customer)}
              disabled={Number(customer.balance) <= 0}
            >
              Record payment
            </Button>
          </Can>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setLedger(customer)}
            aria-label={`View ${customer.name}'s ledger`}
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
        <PageHeader title="Customer Dues" description="What your customers owe you." />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to customer dues"
              description="This screen requires the customers:read permission. Ask an administrator to grant you a role that includes it."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Customer Dues"
        description="Outstanding balances across your customers, with each account's ledger and payments."
      />

      <Card>
        <CardHeader className="flex-col items-stretch gap-3 sm:flex-row sm:items-center">
          <div className="shrink-0">
            <CardTitle>Accounts receivable</CardTitle>
            <CardDescription>
              {listQuery.data
                ? `${listQuery.data.total} customer${listQuery.data.total === 1 ? "" : "s"}`
                : "Loading customers"}
            </CardDescription>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:flex sm:min-w-0 sm:flex-nowrap sm:items-center sm:gap-3 sm:overflow-x-auto sm:pb-0.5">
            <DataTableSearch
              value={table.search}
              onValueChange={table.setSearch}
              placeholder="Search name, phone or email"
              ariaLabel="Search customers"
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
            rows={customers}
            rowKey={(customer) => customer.id}
            isLoading={listQuery.isPending}
            error={listQuery.error}
            onRetry={() => void listQuery.refetch()}
            emptyIcon={Wallet}
            emptyTitle={table.query ? "No customers match your search" : "No outstanding dues"}
            emptyDescription={
              table.query
                ? "Try a different name, phone or email."
                : "Every customer's account is settled."
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
        <CustomerPaymentDialog
          customer={paying}
          onClose={() => setPaying(null)}
          onPaid={refresh}
        />
      ) : null}

      {ledger ? (
        <LedgerDialog
          title={`${ledger.name} — account statement`}
          description="Every charge, payment and refund on this customer's account, with a running balance."
          cacheKey={`customer:${ledger.id}`}
          fetchStatement={(params) => customersApi.ledger(ledger.id, params)}
          onClose={() => setLedger(null)}
        />
      ) : null}
    </PageContainer>
  );
}
