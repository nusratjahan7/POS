"use client";

import { useQuery } from "@tanstack/react-query";

import { ChartCard } from "@/components/reports/chart-card";
import { FinancialBarChart } from "@/components/reports/financial-bar-chart";
import { KpiCard } from "@/components/reports/kpi-card";
import { ReportSkeleton } from "@/components/reports/report-skeleton";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { describeError } from "@/lib/api/client";
import { reportsApi, type ReportParams } from "@/lib/api/reports";
import { formatMoney } from "@/lib/format";

export function FinancialReportTab({
  params,
  currency,
}: {
  params: ReportParams;
  currency: string;
}) {
  const query = useQuery({
    queryKey: ["reports", "financial", params],
    queryFn: () => reportsApi.financial(params),
  });

  if (query.isPending) return <ReportSkeleton />;
  if (query.isError || !query.data) {
    return (
      <ErrorState
        title="Could not load the financial report"
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
  const money = (value: string) => formatMoney(value, currency);

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Revenue" value={money(report.revenue)} hint="Net of returns" />
        <KpiCard label="Cost of goods" value={money(report.cost)} />
        <KpiCard
          label="Gross profit"
          value={money(report.gross_profit)}
          hint={`${report.gross_margin}% margin`}
        />
        <KpiCard label="Expenses" value={money(report.expenses)} />
        <KpiCard label="Net profit" value={money(report.net_profit)} hint="Gross profit less expenses" />
        <KpiCard label="Customer due" value={money(report.customer_due)} hint="Receivable" />
        <KpiCard label="Supplier due" value={money(report.supplier_due)} hint="Payable" />
      </div>

      <ChartCard title="Revenue, cost and profit" description="How the period's money breaks down.">
        <FinancialBarChart report={report} currency={currency} />
      </ChartCard>
    </div>
  );
}
