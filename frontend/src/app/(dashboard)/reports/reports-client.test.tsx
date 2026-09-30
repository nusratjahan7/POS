import type * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ReportsClient } from "./reports-client";

const { salesReport, exportFile, downloadBlob, printHtmlDocument, useAuthMock } = vi.hoisted(() => ({
  salesReport: vi.fn(),
  exportFile: vi.fn(),
  downloadBlob: vi.fn(),
  printHtmlDocument: vi.fn(),
  useAuthMock: vi.fn(),
}));

vi.mock("@/components/auth/auth-provider", () => ({ useAuth: () => useAuthMock() }));

vi.mock("@/lib/api/reports", () => ({
  reportsApi: {
    sales: salesReport,
    purchases: vi.fn(),
    inventory: vi.fn(),
    financial: vi.fn(),
    export: exportFile,
  },
}));

vi.mock("@/lib/api/settings", () => ({
  businessApi: { get: vi.fn().mockResolvedValue({ currency: "USD" }) },
}));

vi.mock("@/lib/api/rbac", () => ({
  branchesApi: { options: vi.fn().mockResolvedValue([]) },
}));

vi.mock("@/lib/download", () => ({ downloadBlob }));
vi.mock("@/lib/reports/print", () => ({ printHtmlDocument }));

// The charts and the HeroUI date picker need real layout APIs jsdom lacks.
vi.mock("@/components/reports/sales-daily-chart", () => ({ SalesDailyChart: () => null }));
vi.mock("@/components/reports/category-bar-chart", () => ({ CategoryBarChart: () => null }));
vi.mock("@/components/reports/payment-method-pie", () => ({ PaymentMethodPie: () => null }));
vi.mock("@/app/(dashboard)/sales/sales-date-range", () => ({ SalesDateRange: () => null }));

vi.mock("@radix-ui/react-select", () => {
  const Pass = ({ children }: { children?: React.ReactNode }) => <>{children}</>;
  return {
    Root: Pass,
    Group: Pass,
    Value: ({ placeholder }: { placeholder?: string }) => <span>{placeholder}</span>,
    Trigger: ({ children }: { children?: React.ReactNode }) => (
      <button type="button">{children}</button>
    ),
    Icon: () => null,
    Portal: Pass,
    Content: Pass,
    Viewport: Pass,
    Item: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
    ItemText: Pass,
    ItemIndicator: () => null,
    ScrollUpButton: () => null,
    ScrollDownButton: () => null,
    Label: Pass,
    Separator: () => null,
  };
});

const report = {
  range: { start: "2026-09-01", end: "2026-09-30", preset: "this_month" },
  summary: {
    total_sales: "100.00",
    order_count: 5,
    average_order_value: "20.00",
    items_sold: "10",
    discount: "0.00",
    tax: "0.00",
    refunded_amount: "0.00",
    returns_count: 0,
  },
  daily: [],
  by_product: [],
  by_category: [],
  by_cashier: [],
  by_branch: [],
  by_payment_method: [],
};

function renderClient() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <ReportsClient />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  useAuthMock.mockReturnValue({ user: { permissions: ["reports:view"] } });
  salesReport.mockResolvedValue(report);
  exportFile.mockResolvedValue({ blob: new Blob(["x"]), filename: "sales.csv" });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ReportsClient", () => {
  it("gates the page behind the reports:view permission", () => {
    useAuthMock.mockReturnValue({ user: { permissions: [] } });
    renderClient();

    expect(screen.getByText("You do not have access to reports")).toBeTruthy();
    expect(salesReport).not.toHaveBeenCalled();
  });

  it("loads the sales report for the default range", async () => {
    renderClient();

    await waitFor(() =>
      expect(salesReport).toHaveBeenCalledWith(expect.objectContaining({ preset: "this_month" })),
    );
    expect(await screen.findByText("Total sales")).toBeTruthy();
    expect(screen.getByText("Sales by product")).toBeTruthy();
  });

  it("downloads the active report as CSV", async () => {
    const user = userEvent.setup();
    renderClient();

    await user.click(screen.getByRole("button", { name: "CSV" }));

    await waitFor(() =>
      expect(exportFile).toHaveBeenCalledWith(
        "sales",
        "csv",
        expect.objectContaining({ preset: "this_month" }),
      ),
    );
    expect(downloadBlob).toHaveBeenCalledWith(expect.any(Blob), "sales.csv");
  });

  it("prints the report as a document", async () => {
    const user = userEvent.setup();
    exportFile.mockResolvedValue({
      blob: new Blob(["<html></html>"], { type: "text/html" }),
      filename: "sales.html",
    });
    renderClient();

    await user.click(screen.getByRole("button", { name: "Print / PDF" }));

    await waitFor(() => expect(printHtmlDocument).toHaveBeenCalled());
  });
});
