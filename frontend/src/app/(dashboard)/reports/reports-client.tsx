"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, Download, FileSpreadsheet, Printer, ShieldAlert } from "lucide-react";
import { toast } from "sonner";

import type { PickedDateRange } from "@/app/(dashboard)/sales/sales-date-range";
import { FinancialReportTab } from "@/app/(dashboard)/reports/financial-report";
import { InventoryReportTab } from "@/app/(dashboard)/reports/inventory-report";
import { ALL_BRANCHES, ReportFilters } from "@/app/(dashboard)/reports/report-filters";
import { PurchasesReportTab } from "@/app/(dashboard)/reports/purchases-report";
import { SalesReportTab } from "@/app/(dashboard)/reports/sales-report";
import { useCan } from "@/components/auth/can";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { describeError } from "@/lib/api/client";
import {
  reportsApi,
  type ReportName,
  type ReportParams,
  type ReportPreset,
} from "@/lib/api/reports";
import { businessApi } from "@/lib/api/settings";
import { downloadBlob } from "@/lib/download";
import { printHtmlDocument } from "@/lib/reports/print";

const TABS: { value: ReportName; label: string; title: string }[] = [
  { value: "sales", label: "Sales", title: "Sales report" },
  { value: "purchases", label: "Purchases", title: "Purchase report" },
  { value: "inventory", label: "Inventory", title: "Inventory report" },
  { value: "financial", label: "Financial", title: "Financial report" },
];

function isoDay(value: PickedDateRange["start"] | undefined): string | undefined {
  return value ? value.toString().slice(0, 10) : undefined;
}

export function ReportsClient() {
  const canRead = useCan("reports:view");

  const [tab, setTab] = React.useState<ReportName>("sales");
  const [preset, setPreset] = React.useState<ReportPreset>("this_month");
  const [range, setRange] = React.useState<PickedDateRange | null>(null);
  const [branchId, setBranchId] = React.useState(ALL_BRANCHES);
  const [exporting, setExporting] = React.useState<"csv" | "xlsx" | "html" | null>(null);

  const businessQuery = useQuery({ queryKey: ["business"], queryFn: () => businessApi.get() });
  const currency = businessQuery.data?.currency ?? "USD";

  const dateFrom = preset === "custom" ? isoDay(range?.start) : undefined;
  const dateTo = preset === "custom" ? isoDay(range?.end) : undefined;
  // A custom range is only runnable once both ends are chosen.
  const ready = preset !== "custom" || Boolean(dateFrom && dateTo);

  const params: ReportParams = {
    preset,
    date_from: dateFrom,
    date_to: dateTo,
    branch_id: branchId === ALL_BRANCHES ? undefined : branchId,
  };

  const activeTab = TABS.find((entry) => entry.value === tab) ?? TABS[0];

  async function handleExport(format: "csv" | "xlsx" | "html") {
    setExporting(format);
    try {
      const file = await reportsApi.export(tab, format, params);
      if (format === "html") {
        printHtmlDocument(await file.blob.text(), activeTab.title);
      } else {
        downloadBlob(file.blob, file.filename);
      }
    } catch (cause) {
      toast.error(describeError(cause));
    } finally {
      setExporting(null);
    }
  }

  if (!canRead) {
    return (
      <PageContainer>
        <PageHeader title="Reports" description="Sales, purchasing, inventory and finance." />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to reports"
              description="This screen requires the reports:view permission. Ask an administrator to grant you a role that includes it."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  const busy = exporting !== null;

  return (
    <PageContainer>
      <PageHeader
        title="Reports"
        description="Every figure is aggregated on the server for the period you choose."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={() => void handleExport("csv")}
              disabled={!ready || busy}
            >
              {exporting === "csv" ? <Spinner /> : <Download className="size-4" />}
              CSV
            </Button>
            <Button
              variant="outline"
              onClick={() => void handleExport("xlsx")}
              disabled={!ready || busy}
            >
              {exporting === "xlsx" ? <Spinner /> : <FileSpreadsheet className="size-4" />}
              Excel
            </Button>
            <Button onClick={() => void handleExport("html")} disabled={!ready || busy}>
              {exporting === "html" ? <Spinner /> : <Printer className="size-4" />}
              Print / PDF
            </Button>
          </div>
        }
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

      {ready ? (
        <Tabs value={tab} onValueChange={(value) => setTab(value as ReportName)}>
          <TabsList>
            {TABS.map((entry) => (
              <TabsTrigger key={entry.value} value={entry.value}>
                {entry.label}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="sales">
            <SalesReportTab params={params} currency={currency} />
          </TabsContent>
          <TabsContent value="purchases">
            <PurchasesReportTab params={params} currency={currency} />
          </TabsContent>
          <TabsContent value="inventory">
            <InventoryReportTab params={params} currency={currency} />
          </TabsContent>
          <TabsContent value="financial">
            <FinancialReportTab params={params} currency={currency} />
          </TabsContent>
        </Tabs>
      ) : (
        <Card>
          <CardContent className="text-muted-foreground flex items-center gap-2 text-sm">
            <BarChart3 className="size-4" aria-hidden />
            Pick a start and end date to run a custom report.
          </CardContent>
        </Card>
      )}
    </PageContainer>
  );
}
