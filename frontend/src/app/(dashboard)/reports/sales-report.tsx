"use client";

import { useQuery } from "@tanstack/react-query";

import type { DataTableColumn } from "@/components/data-table/data-table";
import { ChartCard } from "@/components/reports/chart-card";
import { KpiCard } from "@/components/reports/kpi-card";
import { PaymentMethodPie } from "@/components/reports/payment-method-pie";
import { ReportSkeleton } from "@/components/reports/report-skeleton";
import { CategoryBarChart } from "@/components/reports/category-bar-chart";
import { SalesDailyChart } from "@/components/reports/sales-daily-chart";
import { TableCard } from "@/components/reports/table-card";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { describeError } from "@/lib/api/client";
import {
  reportsApi,
  type CategorySalesRow,
  type CashierSalesRow,
  type PaymentMethodSalesRow,
  type ProductSalesRow,
  type ReportParams,
  type BranchSalesRow,
} from "@/lib/api/reports";
import { formatMoney, formatQuantity } from "@/lib/format";

export function SalesReportTab({ params, currency }: { params: ReportParams; currency: string }) {
  const query = useQuery({
    queryKey: ["reports", "sales", params],
    queryFn: () => reportsApi.sales(params),
  });

  if (query.isPending) return <ReportSkeleton />;
  if (query.isError || !query.data) {
    return (
      <ErrorState
        title="Could not load the sales report"
        description={describeError(query.error)}
        action={
          <Button variant="outline" onClick={() => void query.refetch()}>
            Try again
          </Button>
        }
      />
    );
  }

  const report = query.data;
  const summary = report.summary;
  const money = (value: string) => formatMoney(value, currency);

  const productColumns: DataTableColumn<ProductSalesRow>[] = [
    { id: "name", header: "Product", cell: (row) => <span className="font-medium">{row.name}</span> },
    { id: "sku", header: "SKU", hideBelow: "md", cell: (row) => <span className="text-muted-foreground text-xs">{row.sku}</span> },
    { id: "quantity", header: "Qty", align: "right", cell: (row) => <span className="tabular-nums">{formatQuantity(row.quantity)}</span> },
    { id: "net", header: "Net", align: "right", cell: (row) => <span className="tabular-nums">{money(row.net)}</span> },
    { id: "cost", header: "Cost", align: "right", hideBelow: "lg", cell: (row) => <span className="tabular-nums">{money(row.cost)}</span> },
    { id: "profit", header: "Profit", align: "right", cell: (row) => <span className="font-medium tabular-nums">{money(row.profit)}</span> },
  ];

  const categoryColumns: DataTableColumn<CategorySalesRow>[] = [
    { id: "name", header: "Category", cell: (row) => <span className="font-medium">{row.name}</span> },
    { id: "quantity", header: "Qty", align: "right", cell: (row) => <span className="tabular-nums">{formatQuantity(row.quantity)}</span> },
    { id: "net", header: "Net", align: "right", cell: (row) => <span className="tabular-nums">{money(row.net)}</span> },
  ];

  const cashierColumns: DataTableColumn<CashierSalesRow>[] = [
    { id: "name", header: "Cashier", cell: (row) => <span className="font-medium">{row.name}</span> },
    { id: "orders", header: "Orders", align: "right", cell: (row) => <span className="tabular-nums">{row.order_count}</span> },
    { id: "total", header: "Sales", align: "right", cell: (row) => <span className="tabular-nums">{money(row.total)}</span> },
  ];

  const branchColumns: DataTableColumn<BranchSalesRow>[] = [
    { id: "name", header: "Branch", cell: (row) => <span className="font-medium">{row.name}</span> },
    { id: "orders", header: "Orders", align: "right", cell: (row) => <span className="tabular-nums">{row.order_count}</span> },
    { id: "total", header: "Sales", align: "right", cell: (row) => <span className="tabular-nums">{money(row.total)}</span> },
  ];

  const methodColumns: DataTableColumn<PaymentMethodSalesRow>[] = [
    { id: "name", header: "Method", cell: (row) => <span className="font-medium">{row.name}</span> },
    { id: "kind", header: "Kind", hideBelow: "md", cell: (row) => <span className="text-muted-foreground text-xs capitalize">{row.kind}</span> },
    { id: "count", header: "Count", align: "right", cell: (row) => <span className="tabular-nums">{row.count}</span> },
    { id: "amount", header: "Amount", align: "right", cell: (row) => <span className="tabular-nums">{money(row.amount)}</span> },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Total sales" value={money(summary.total_sales)} hint={`${money(summary.refunded_amount)} refunded`} />
        <KpiCard label="Orders" value={String(summary.order_count)} hint={`${summary.returns_count} returns`} />
        <KpiCard label="Average order value" value={money(summary.average_order_value)} />
        <KpiCard label="Items sold" value={formatQuantity(summary.items_sold)} hint={`${money(summary.discount)} discounted`} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Revenue trend" description="Net sales per day.">
          <SalesDailyChart data={report.daily} currency={currency} />
        </ChartCard>
        <ChartCard title="Sales by category" description="Top categories by net sales.">
          <CategoryBarChart data={report.by_category} currency={currency} />
        </ChartCard>
      </div>

      <ChartCard title="Tendered by payment method" description="How the period's takings were paid.">
        <PaymentMethodPie data={report.by_payment_method} currency={currency} />
      </ChartCard>

      <TableCard
        title="Sales by product"
        columns={productColumns}
        rows={report.by_product}
        rowKey={(row) => row.product_id ?? row.sku}
        emptyTitle="No products sold in this period"
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <TableCard
          title="Sales by category"
          columns={categoryColumns}
          rows={report.by_category}
          rowKey={(row) => row.category_id ?? row.name}
          emptyTitle="No category sales"
        />
        <TableCard
          title="Sales by payment method"
          columns={methodColumns}
          rows={report.by_payment_method}
          rowKey={(row) => row.payment_method_id ?? row.name}
          emptyTitle="No payments recorded"
        />
        <TableCard
          title="Sales by cashier"
          columns={cashierColumns}
          rows={report.by_cashier}
          rowKey={(row) => row.cashier_id ?? row.name}
          emptyTitle="No cashier sales"
        />
        <TableCard
          title="Sales by branch"
          columns={branchColumns}
          rows={report.by_branch}
          rowKey={(row) => row.branch_id ?? row.name}
          emptyTitle="No branch sales"
        />
      </div>
    </div>
  );
}
