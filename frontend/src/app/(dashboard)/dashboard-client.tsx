"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Banknote,
  HandCoins,
  LayoutDashboard,
  Package,
  PiggyBank,
  ShieldAlert,
  ShoppingCart,
  TrendingUp,
  TriangleAlert,
  Users,
} from "lucide-react";

import { ALL_BRANCHES, ReportFilters } from "@/app/(dashboard)/reports/report-filters";
import type { PickedDateRange } from "@/app/(dashboard)/sales/sales-date-range";
import { useCan } from "@/components/auth/can";
import { OrdersTrendChart } from "@/components/dashboard/orders-trend-chart";
import { ProfitTrendChart } from "@/components/dashboard/profit-trend-chart";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import type { DataTableColumn } from "@/components/data-table/data-table";
import { CategoryBarChart } from "@/components/reports/category-bar-chart";
import { ChartCard } from "@/components/reports/chart-card";
import { KpiCard } from "@/components/reports/kpi-card";
import { PaymentMethodPie } from "@/components/reports/payment-method-pie";
import { ReportSkeleton } from "@/components/reports/report-skeleton";
import { SalesDailyChart } from "@/components/reports/sales-daily-chart";
import { TableCard } from "@/components/reports/table-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { describeError } from "@/lib/api/client";
import {
  dashboardApi,
  type RecentPaymentRow,
  type RecentSaleRow,
  type TrendPoint,
} from "@/lib/api/dashboard";
import type {
  ProductSalesRow,
  ReportPreset,
  SalesDailyPoint,
  StockStatusRow,
} from "@/lib/api/reports";
import { businessApi } from "@/lib/api/settings";
import { formatDateTime, formatMoney, formatQuantity } from "@/lib/format";

const PERIOD_LABEL: Record<ReportPreset, string> = {
  today: "today",
  yesterday: "yesterday",
  this_week: "this week",
  this_month: "this month",
  this_year: "this year",
  custom: "the selected period",
};

const SALE_STATUS_VARIANT: Record<string, "success" | "destructive" | "warning" | "neutral"> = {
  completed: "success",
  voided: "destructive",
  refunded: "warning",
};

function isoDay(value: PickedDateRange["start"] | undefined): string | undefined {
  return value ? value.toString().slice(0, 10) : undefined;
}

function SectionHeading({ title, aside }: { title: React.ReactNode; aside?: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1 border-b pb-2 sm:flex-row sm:items-end sm:justify-between sm:gap-4">
      <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
      {aside ? <span className="text-muted-foreground text-xs">{aside}</span> : null}
    </div>
  );
}

export function DashboardClient() {
  const canRead = useCan("dashboard:view");

  const [preset, setPreset] = React.useState<ReportPreset>("this_week");
  const [range, setRange] = React.useState<PickedDateRange | null>(null);
  const [branchId, setBranchId] = React.useState(ALL_BRANCHES);

  const dateFrom = preset === "custom" ? isoDay(range?.start) : undefined;
  const dateTo = preset === "custom" ? isoDay(range?.end) : undefined;
  const ready = preset !== "custom" || Boolean(dateFrom && dateTo);

  const params = {
    preset,
    date_from: dateFrom,
    date_to: dateTo,
    branch_id: branchId === ALL_BRANCHES ? undefined : branchId,
  };

  const businessQuery = useQuery({ queryKey: ["business"], queryFn: () => businessApi.get() });
  const currency = businessQuery.data?.currency ?? "USD";

  const query = useQuery({
    queryKey: ["dashboard", params],
    queryFn: () => dashboardApi.snapshot(params),
    enabled: canRead && ready,
  });

  if (!canRead) {
    return (
      <PageContainer>
        <PageHeader title="Dashboard" description="A live view of trade and stock." />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to the dashboard"
              description="This screen requires the dashboard:view permission. Ask an administrator for a role that includes it."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  const money = (value: string) => formatMoney(value, currency);

  return (
    <PageContainer>
      <PageHeader
        title="Dashboard"
        description={`Today at a glance, plus ${PERIOD_LABEL[preset]} trade and where the business stands right now.`}
      />

      <ReportFilters
        preset={preset}
        onPresetChange={(next) => {
          setPreset(next);
          if (next !== "custom") setRange(null);
        }}
        range={range}
        onRangeChange={setRange}
        branchId={branchId}
        onBranchChange={setBranchId}
      />

      {!ready ? (
        <Card>
          <CardContent className="text-muted-foreground flex items-center gap-2 text-sm">
            <LayoutDashboard className="size-4" aria-hidden />
            Pick a start and end date to load a custom period.
          </CardContent>
        </Card>
      ) : query.isPending ? (
        <ReportSkeleton />
      ) : query.isError || !query.data ? (
        <ErrorState
          title="Could not load the dashboard"
          description={describeError(query.error)}
          action={
            <Button variant="outline" onClick={() => void query.refetch()}>
              Try again
            </Button>
          }
        />
      ) : (
        <DashboardSnapshotView
          snapshot={query.data}
          currency={currency}
          money={money}
          period={PERIOD_LABEL[preset]}
        />
      )}
    </PageContainer>
  );
}

function DashboardSnapshotView({
  snapshot,
  currency,
  money,
  period,
}: {
  snapshot: Awaited<ReturnType<typeof dashboardApi.snapshot>>;
  currency: string;
  money: (value: string) => string;
  period: string;
}) {
  const { today, standing, trends } = snapshot;

  const revenuePoints: SalesDailyPoint[] = trends.map((point) => ({
    day: point.day,
    total: point.revenue,
    orders: point.orders,
  }));

  const productColumns: DataTableColumn<ProductSalesRow>[] = [
    { id: "name", header: "Product", cell: (row) => <span className="font-medium">{row.name}</span> },
    {
      id: "sku",
      header: "SKU",
      hideBelow: "md",
      cell: (row) => <span className="text-muted-foreground text-xs">{row.sku}</span>,
    },
    {
      id: "quantity",
      header: "Sold",
      align: "right",
      cell: (row) => <span className="tabular-nums">{formatQuantity(row.quantity)}</span>,
    },
    {
      id: "net",
      header: "Net",
      align: "right",
      cell: (row) => <span className="tabular-nums">{money(row.net)}</span>,
    },
    {
      id: "profit",
      header: "Profit",
      align: "right",
      cell: (row) => <span className="font-medium tabular-nums">{money(row.profit)}</span>,
    },
  ];

  const saleColumns: DataTableColumn<RecentSaleRow>[] = [
    {
      id: "sale_number",
      header: "Sale",
      cell: (row) => <span className="font-medium tabular-nums">{row.sale_number}</span>,
    },
    {
      id: "customer",
      header: "Customer",
      hideBelow: "md",
      cell: (row) => (
        <span className="text-muted-foreground">{row.customer_name ?? "Walk-in"}</span>
      ),
    },
    {
      id: "total",
      header: "Total",
      align: "right",
      cell: (row) => <span className="tabular-nums">{money(row.total)}</span>,
    },
    {
      id: "status",
      header: "Status",
      align: "right",
      cell: (row) => (
        <Badge variant={SALE_STATUS_VARIANT[row.status] ?? "neutral"}>{row.status}</Badge>
      ),
    },
    {
      id: "sold_at",
      header: "Time",
      align: "right",
      hideBelow: "lg",
      cell: (row) => <span className="text-muted-foreground text-xs">{formatDateTime(row.sold_at)}</span>,
    },
  ];

  const lowStockColumns: DataTableColumn<StockStatusRow>[] = [
    { id: "name", header: "Product", cell: (row) => <span className="font-medium">{row.name}</span> },
    {
      id: "sku",
      header: "SKU",
      hideBelow: "md",
      cell: (row) => <span className="text-muted-foreground text-xs">{row.sku}</span>,
    },
    {
      id: "quantity",
      header: "On hand",
      align: "right",
      cell: (row) => <span className="tabular-nums">{formatQuantity(row.quantity)}</span>,
    },
    {
      id: "minimum_stock",
      header: "Reorder at",
      align: "right",
      cell: (row) => (
        <span className="text-muted-foreground tabular-nums">
          {formatQuantity(row.minimum_stock)}
        </span>
      ),
    },
  ];

  const paymentColumns: DataTableColumn<RecentPaymentRow>[] = [
    {
      id: "sale_number",
      header: "Sale",
      cell: (row) => <span className="font-medium tabular-nums">{row.sale_number}</span>,
    },
    { id: "method_name", header: "Method", cell: (row) => row.method_name },
    {
      id: "amount",
      header: "Amount",
      align: "right",
      cell: (row) => <span className="font-medium tabular-nums">{money(row.amount)}</span>,
    },
    {
      id: "paid_at",
      header: "Time",
      align: "right",
      hideBelow: "lg",
      cell: (row) => (
        <span className="text-muted-foreground text-xs">{formatDateTime(row.paid_at)}</span>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-8">
      <section className="flex flex-col gap-4">
        <SectionHeading title="Today" aside={`Updated ${formatDateTime(snapshot.as_of)}`} />

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard label="Today's sales" value={money(today.sales)} icon={Banknote} accent />
          <KpiCard label="Today's orders" value={String(today.orders)} icon={ShoppingCart} />
          <KpiCard label="Gross profit" value={money(today.gross_profit)} icon={TrendingUp} />
          <KpiCard label="Net profit" value={money(today.net_profit)} icon={PiggyBank} />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <SectionHeading title="Right now" aside="Live totals, unaffected by the date range" />

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard label="Customers" value={String(standing.customers)} icon={Users} />
          <KpiCard label="Products" value={String(standing.products)} icon={Package} />
          <KpiCard
            label="Low stock"
            value={String(standing.low_stock)}
            icon={TriangleAlert}
            tone={standing.low_stock > 0 ? "warning" : "default"}
            hint={standing.low_stock > 0 ? "At or below reorder level" : "Everything stocked"}
          />
          <KpiCard
            label="Outstanding due"
            value={money(standing.outstanding_due)}
            icon={HandCoins}
            hint={`Supplier due ${money(standing.supplier_due)}`}
          />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <SectionHeading title={`Trends · ${period}`} aside="Net revenue per day" />

        <ChartCard
          title="Revenue trend"
          description="Net revenue per day."
          contentClassName="h-80"
        >
          <SalesDailyChart data={revenuePoints} currency={currency} />
        </ChartCard>

        <div className="grid gap-4 lg:grid-cols-2">
          <ChartCard title="Profit trend" description="Revenue less cost of goods and expenses.">
            <ProfitTrendChart data={trends} currency={currency} />
          </ChartCard>
          <ChartCard title="Sales trend" description="Orders rung up per day.">
            <OrdersTrendChart data={trends} />
          </ChartCard>
          <ChartCard title="Payment methods" description="How the period's takings were paid.">
            <PaymentMethodPie data={snapshot.payment_methods} currency={currency} />
          </ChartCard>
          <ChartCard title="Category performance" description="Top categories by net sales.">
            <CategoryBarChart data={snapshot.category_performance} currency={currency} />
          </ChartCard>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <SectionHeading title="Detail" />

        <div className="grid gap-4 lg:grid-cols-2">
          <TableCard
            title="Top-selling products"
            columns={productColumns}
            rows={snapshot.top_products}
            rowKey={(row) => row.product_id ?? row.sku}
            emptyTitle="Nothing sold in this period"
          />
          <TableCard
            title="Recent sales"
            columns={saleColumns}
            rows={snapshot.recent_sales}
            rowKey={(row) => row.id}
            emptyTitle="No sales yet"
          />
          <TableCard
            title="Low-stock products"
            columns={lowStockColumns}
            rows={snapshot.low_stock}
            rowKey={(row) => row.product_id}
            emptyTitle="Everything is well stocked"
          />
          <TableCard
            title="Recent payments"
            columns={paymentColumns}
            rows={snapshot.recent_payments}
            rowKey={(row) => row.id}
            emptyTitle="No payments recorded"
          />
        </div>
      </section>
    </div>
  );
}
