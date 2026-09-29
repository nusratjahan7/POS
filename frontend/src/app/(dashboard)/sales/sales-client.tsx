"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Eye, Printer, Receipt, ShieldAlert } from "lucide-react";

import { SaleDetailsDialog } from "@/app/(dashboard)/sales/sale-details-dialog";
import { SalesDateRange, type PickedDateRange } from "@/app/(dashboard)/sales/sales-date-range";
import { useCan } from "@/components/auth/can";
import { DataTable, type DataTableColumn } from "@/components/data-table/data-table";
import { DataTablePagination } from "@/components/data-table/data-table-pagination";
import { DataTableSearch } from "@/components/data-table/data-table-search";
import { SelectFilter } from "@/components/data-table/select-filter";
import { useDataTable } from "@/components/data-table/use-data-table";
import { InvoicePreviewDialog } from "@/components/invoice/invoice-preview-dialog";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { PaymentStatusBadge, SaleStatusBadge } from "@/components/sales/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { customersApi } from "@/lib/api/customers";
import {
  salesApi,
  type PaymentStatus,
  type SaleStatus,
  type SaleSummary,
} from "@/lib/api/sales";
import { businessApi } from "@/lib/api/settings";
import { formatDateTime, formatMoney } from "@/lib/format";

const ALL = "all";

const PAYMENT_OPTIONS = [
  { value: ALL, label: "All payments" },
  { value: "paid", label: "Paid" },
  { value: "partial", label: "Partially paid" },
  { value: "unpaid", label: "Unpaid" },
];

const SALES_OPTIONS = [
  { value: ALL, label: "All sales" },
  { value: "completed", label: "Completed" },
  { value: "refunded", label: "Refunded" },
  { value: "voided", label: "Voided" },
];

const SORT_OPTIONS = [
  { value: "-sold_at", label: "Newest first" },
  { value: "sold_at", label: "Oldest first" },
  { value: "-total", label: "Total: high to low" },
  { value: "total", label: "Total: low to high" },
  { value: "sale_number", label: "Invoice: A to Z" },
];

export function SalesClient() {
  const canRead = useCan("sales:read");
  const canReadBusiness = useCan("business:read");

  const table = useDataTable();
  const [customer, setCustomer] = React.useState(ALL);
  const [cashier, setCashier] = React.useState(ALL);
  const [payment, setPayment] = React.useState(ALL);
  const [status, setStatus] = React.useState(ALL);
  const [range, setRange] = React.useState<PickedDateRange | null>(null);
  const [sort, setSort] = React.useState("-sold_at");
  const [detailId, setDetailId] = React.useState<string | null>(null);
  const [printId, setPrintId] = React.useState<string | null>(null);

  // The calendar yields CalendarDates; the API wants plain YYYY-MM-DD bounds.
  const dateFrom = range ? range.start.toString().slice(0, 10) : "";
  const dateTo = range ? range.end.toString().slice(0, 10) : "";

  const listQuery = useQuery({
    queryKey: [
      "sales",
      {
        query: table.query,
        page: table.page,
        customer,
        cashier,
        payment,
        status,
        dateFrom,
        dateTo,
        sort,
      },
    ],
    queryFn: () =>
      salesApi.list({
        search: table.query || undefined,
        page: table.page,
        customer_id: customer === ALL ? undefined : customer,
        cashier_id: cashier === ALL ? undefined : cashier,
        payment_status: payment === ALL ? undefined : (payment as PaymentStatus),
        status: status === ALL ? undefined : (status as SaleStatus),
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        sort,
      }),
    enabled: canRead,
  });

  const customersQuery = useQuery({
    queryKey: ["customers", "options"],
    queryFn: () => customersApi.options(),
    enabled: canRead,
  });

  const cashiersQuery = useQuery({
    queryKey: ["sales", "cashiers"],
    queryFn: () => salesApi.cashierOptions(),
    enabled: canRead,
  });

  const businessQuery = useQuery({
    queryKey: ["business"],
    queryFn: () => businessApi.get(),
    enabled: canReadBusiness,
  });

  const sales = listQuery.data?.items ?? [];
  const currency = businessQuery.data?.currency ?? "USD";

  const customerOptions = React.useMemo(
    () => [
      { value: ALL, label: "All customers" },
      ...(customersQuery.data ?? []).map((option) => ({
        value: option.id,
        label: option.name,
      })),
    ],
    [customersQuery.data],
  );

  const cashierOptions = React.useMemo(
    () => [
      { value: ALL, label: "All cashiers" },
      ...(cashiersQuery.data ?? []).map((option) => ({
        value: option.id,
        label: option.full_name,
      })),
    ],
    [cashiersQuery.data],
  );

  const columns: DataTableColumn<SaleSummary>[] = [
    {
      id: "invoice",
      header: "Invoice",
      cell: (sale) => (
        <span className="font-mono text-xs font-medium">{sale.sale_number}</span>
      ),
    },
    {
      id: "date",
      header: "Date",
      hideBelow: "md",
      cell: (sale) => (
        <span className="text-muted-foreground text-sm">{formatDateTime(sale.sold_at)}</span>
      ),
    },
    {
      id: "customer",
      header: "Customer",
      cell: (sale) => (
        <span className="truncate text-sm">{sale.customer?.name ?? "Walk-in"}</span>
      ),
    },
    {
      id: "cashier",
      header: "Cashier",
      hideBelow: "lg",
      cell: (sale) => (
        <span className="text-muted-foreground text-sm">{sale.cashier?.full_name ?? "—"}</span>
      ),
    },
    {
      id: "branch",
      header: "Branch",
      hideBelow: "lg",
      cell: (sale) => (
        <span className="text-muted-foreground text-sm">{sale.branch.name}</span>
      ),
    },
    {
      id: "items",
      header: "Items",
      align: "right",
      hideBelow: "md",
      cell: (sale) => <span className="tabular-nums">{sale.item_count}</span>,
    },
    {
      id: "subtotal",
      header: "Subtotal",
      align: "right",
      hideBelow: "lg",
      cell: (sale) => (
        <span className="text-muted-foreground text-sm tabular-nums">
          {formatMoney(sale.subtotal, currency)}
        </span>
      ),
    },
    {
      id: "discount",
      header: "Discount",
      align: "right",
      hideBelow: "lg",
      cell: (sale) => (
        <span className="text-muted-foreground text-sm tabular-nums">
          {formatMoney(sale.discount, currency)}
        </span>
      ),
    },
    {
      id: "total",
      header: "Total",
      align: "right",
      cell: (sale) => (
        <span className="font-medium tabular-nums">{formatMoney(sale.total, currency)}</span>
      ),
    },
    {
      id: "paid",
      header: "Paid",
      align: "right",
      hideBelow: "lg",
      cell: (sale) => (
        <span className="text-sm tabular-nums">{formatMoney(sale.paid, currency)}</span>
      ),
    },
    {
      id: "due",
      header: "Due",
      align: "right",
      hideBelow: "md",
      cell: (sale) => (
        <span className="text-sm tabular-nums">{formatMoney(sale.due, currency)}</span>
      ),
    },
    {
      id: "payment_status",
      header: "Payment",
      cell: (sale) => <PaymentStatusBadge sale={sale} />,
    },
    {
      id: "status",
      header: "Status",
      cell: (sale) => <SaleStatusBadge status={sale.status} />,
    },
    {
      id: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (sale) => (
        <div className="flex items-center justify-end gap-1">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setDetailId(sale.id)}
            aria-label={`View ${sale.sale_number}`}
          >
            <Eye className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setPrintId(sale.id)}
            aria-label={`Print ${sale.sale_number}`}
          >
            <Printer className="size-4" />
          </Button>
        </div>
      ),
    },
  ];

  if (!canRead) {
    return (
      <PageContainer>
        <PageHeader
          title="Sales"
          description="Every sale rung up, with its settlement and status."
        />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to sales"
              description="This screen requires the sales:read permission. Ask an administrator to grant you a role that includes it."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Sales"
        description="Every sale rung up, with its settlement, status and receipt."
      />

      <Card>
        <CardHeader className="flex-col items-stretch gap-3 sm:flex-row sm:items-center">
          <div className="shrink-0">
            <CardTitle>All sales</CardTitle>
            <CardDescription>
              {listQuery.data
                ? `${listQuery.data.total} sale${listQuery.data.total === 1 ? "" : "s"}`
                : "Loading sales"}
            </CardDescription>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:flex sm:min-w-0 sm:flex-wrap sm:items-center sm:gap-3">
            <DataTableSearch
              value={table.search}
              onValueChange={table.setSearch}
              placeholder="Search invoice number"
              ariaLabel="Search sales by invoice number"
              className="col-span-2"
            />
            <SelectFilter
              value={customer}
              onValueChange={(value) => {
                setCustomer(value);
                table.resetPage();
              }}
              options={customerOptions}
              ariaLabel="Filter by customer"
              className="sm:w-56"
            />
            <SelectFilter
              value={cashier}
              onValueChange={(value) => {
                setCashier(value);
                table.resetPage();
              }}
              options={cashierOptions}
              ariaLabel="Filter by cashier"
              className="sm:w-56"
            />
            <SelectFilter
              value={payment}
              onValueChange={(value) => {
                setPayment(value);
                table.resetPage();
              }}
              options={PAYMENT_OPTIONS}
              ariaLabel="Filter by payment status"
              className="sm:w-40"
            />
            <SelectFilter
              value={status}
              onValueChange={(value) => {
                setStatus(value);
                table.resetPage();
              }}
              options={SALES_OPTIONS}
              ariaLabel="Filter by sale status"
              className="sm:w-40"
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
              ariaLabel="Sort sales"
              className="sm:w-44"
            />
          </div>
        </CardHeader>

        <CardContent>
          <DataTable
            columns={columns}
            rows={sales}
            rowKey={(sale) => sale.id}
            isLoading={listQuery.isPending}
            error={listQuery.error}
            onRetry={() => void listQuery.refetch()}
            emptyIcon={Receipt}
            emptyTitle={
              table.query ? "No sales match your search" : "No sales match these filters"
            }
            emptyDescription={
              table.query
                ? "Check the invoice number, or clear the search."
                : "Adjust or clear the filters to see more sales."
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
        <SaleDetailsDialog
          saleId={detailId}
          onClose={() => setDetailId(null)}
          onChanged={() => void listQuery.refetch()}
        />
      ) : null}

      {printId ? (
        <InvoicePreviewDialog saleId={printId} onClose={() => setPrintId(null)} />
      ) : null}
    </PageContainer>
  );
}
