"use client";

import { useQuery } from "@tanstack/react-query";

import type { DataTableColumn } from "@/components/data-table/data-table";
import { KpiCard } from "@/components/reports/kpi-card";
import { ReportSkeleton } from "@/components/reports/report-skeleton";
import { TableCard } from "@/components/reports/table-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { describeError } from "@/lib/api/client";
import {
  reportsApi,
  type MovementTypeRow,
  type ReportParams,
  type StockStatusRow,
} from "@/lib/api/reports";
import { formatMoney, formatQuantity } from "@/lib/format";

const MOVEMENT_LABELS: Record<string, string> = {
  opening: "Opening",
  stock_in: "Stock in",
  stock_out: "Stock out",
  adjustment: "Adjustment",
  damage: "Damage",
  return: "Return",
};

export function InventoryReportTab({
  params,
  currency,
}: {
  params: ReportParams;
  currency: string;
}) {
  const query = useQuery({
    queryKey: ["reports", "inventory", params],
    queryFn: () => reportsApi.inventory(params),
  });

  if (query.isPending) return <ReportSkeleton />;
  if (query.isError || !query.data) {
    return (
      <ErrorState
        title="Could not load the inventory report"
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
  const totals = report.totals;

  const stockColumns: DataTableColumn<StockStatusRow>[] = [
    { id: "name", header: "Product", cell: (row) => <span className="font-medium">{row.name}</span> },
    { id: "sku", header: "SKU", hideBelow: "md", cell: (row) => <span className="text-muted-foreground text-xs">{row.sku}</span> },
    { id: "quantity", header: "On hand", align: "right", cell: (row) => <span className="tabular-nums">{formatQuantity(row.quantity)}</span> },
    { id: "minimum", header: "Minimum", align: "right", hideBelow: "lg", cell: (row) => <span className="tabular-nums">{formatQuantity(row.minimum_stock)}</span> },
    {
      id: "status",
      header: "Status",
      cell: (row) => (
        <Badge variant={row.stock_status === "out_of_stock" ? "destructive" : "warning"}>
          {row.stock_status === "out_of_stock" ? "Out of stock" : "Low"}
        </Badge>
      ),
    },
  ];

  const movementColumns: DataTableColumn<MovementTypeRow>[] = [
    {
      id: "type",
      header: "Movement",
      cell: (row) => <span className="font-medium">{MOVEMENT_LABELS[row.movement_type] ?? row.movement_type}</span>,
    },
    { id: "count", header: "Count", align: "right", cell: (row) => <span className="tabular-nums">{row.count}</span> },
    {
      id: "net",
      header: "Net quantity",
      align: "right",
      cell: (row) => <span className="tabular-nums">{formatQuantity(row.net_quantity)}</span>,
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Stock value (cost)"
          value={formatMoney(totals.stock_value_cost, currency)}
          hint={`${formatMoney(totals.stock_value_retail, currency)} at retail`}
        />
        <KpiCard
          label="Products tracked"
          value={String(totals.product_count)}
          hint={`${formatQuantity(totals.total_quantity)} units on hand`}
        />
        <KpiCard
          label="In stock"
          value={String(totals.in_stock)}
          hint={`${totals.low_stock} low`}
        />
        <KpiCard
          label="Out of stock"
          value={String(totals.out_of_stock)}
          hint={`${report.adjustments.count} adjustments this period`}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <TableCard
          title="Low stock"
          description="At or below the minimum level."
          columns={stockColumns}
          rows={report.low_stock}
          rowKey={(row) => row.product_id}
          emptyTitle="Nothing is low on stock"
        />
        <TableCard
          title="Out of stock"
          columns={stockColumns}
          rows={report.out_of_stock}
          rowKey={(row) => row.product_id}
          emptyTitle="Everything is in stock"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <TableCard
          title="Stock movements"
          description="Every change to on-hand stock in this period."
          columns={movementColumns}
          rows={report.movements}
          rowKey={(row) => row.movement_type}
          emptyTitle="No stock moved in this period"
        />

        <div className="grid gap-4 sm:grid-cols-2">
          <KpiCard label="Adjustments" value={String(report.adjustments.count)} />
          <KpiCard
            label="Adjustment quantity"
            value={formatQuantity(report.adjustments.net_quantity)}
          />
          <KpiCard label="Damages" value={String(report.adjustments.damage_count)} />
          <KpiCard
            label="Damage quantity"
            value={formatQuantity(report.adjustments.damage_quantity)}
          />
        </div>
      </div>
    </div>
  );
}
