"use client";

import { useQuery } from "@tanstack/react-query";

import type { DataTableColumn } from "@/components/data-table/data-table";
import { KpiCard } from "@/components/reports/kpi-card";
import { ReportSkeleton } from "@/components/reports/report-skeleton";
import { TableCard } from "@/components/reports/table-card";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { describeError } from "@/lib/api/client";
import { reportsApi, type ReportParams, type SupplierPurchaseRow } from "@/lib/api/reports";
import { formatMoney } from "@/lib/format";

export function PurchasesReportTab({
  params,
  currency,
}: {
  params: ReportParams;
  currency: string;
}) {
  const query = useQuery({
    queryKey: ["reports", "purchases", params],
    queryFn: () => reportsApi.purchases(params),
  });

  if (query.isPending) return <ReportSkeleton />;
  if (query.isError || !query.data) {
    return (
      <ErrorState
        title="Could not load the purchase report"
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

  const supplierColumns: DataTableColumn<SupplierPurchaseRow>[] = [
    { id: "name", header: "Supplier", cell: (row) => <span className="font-medium">{row.name}</span> },
    { id: "count", header: "Orders", align: "right", cell: (row) => <span className="tabular-nums">{row.count}</span> },
    { id: "total", header: "Total", align: "right", cell: (row) => <span className="tabular-nums">{money(row.total)}</span> },
    { id: "due", header: "Due", align: "right", cell: (row) => <span className="font-medium tabular-nums">{money(row.due)}</span> },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Total purchases" value={money(summary.total_purchases)} />
        <KpiCard label="Orders" value={String(summary.purchase_count)} />
        <KpiCard label="Paid" value={money(summary.paid)} />
        <KpiCard
          label="Outstanding due"
          value={money(summary.outstanding_due)}
          hint="Owed to suppliers, all time"
        />
      </div>

      <TableCard
        title="Purchases by supplier"
        description="Received orders in this period."
        columns={supplierColumns}
        rows={report.by_supplier}
        rowKey={(row) => row.supplier_id ?? row.name}
        emptyTitle="No purchases in this period"
      />
    </div>
  );
}
