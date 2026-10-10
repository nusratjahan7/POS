import type * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { DashboardClient } from "./dashboard-client";

const { snapshot, useAuthMock } = vi.hoisted(() => ({
  snapshot: vi.fn(),
  useAuthMock: vi.fn(),
}));

vi.mock("@/components/auth/auth-provider", () => ({ useAuth: () => useAuthMock() }));

vi.mock("@/lib/api/dashboard", () => ({
  dashboardApi: { snapshot },
}));

vi.mock("@/lib/api/settings", () => ({
  businessApi: { get: vi.fn().mockResolvedValue({ currency: "USD" }) },
}));

vi.mock("@/lib/api/rbac", () => ({
  branchesApi: { options: vi.fn().mockResolvedValue([]) },
}));

// The charts and the HeroUI date picker need real layout APIs jsdom lacks.
vi.mock("@/components/dashboard/orders-trend-chart", () => ({ OrdersTrendChart: () => null }));
vi.mock("@/components/dashboard/profit-trend-chart", () => ({ ProfitTrendChart: () => null }));
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

const data = {
  as_of: "2026-10-10T09:00:00Z",
  range: { start: "2026-10-05", end: "2026-10-10", preset: "this_week" },
  today: { sales: "120.00", orders: 3, gross_profit: "40.00", net_profit: "25.00" },
  standing: {
    customers: 5,
    products: 12,
    low_stock: 2,
    outstanding_due: "10.00",
    supplier_due: "0.00",
  },
  trends: [{ day: "2026-10-10", orders: 3, revenue: "120.00", profit: "25.00" }],
  category_performance: [],
  payment_methods: [],
  top_products: [],
  recent_sales: [],
  low_stock: [],
  recent_payments: [],
};

function renderClient() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <DashboardClient />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  useAuthMock.mockReturnValue({ user: { permissions: ["dashboard:view"] } });
  snapshot.mockResolvedValue(data);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("DashboardClient", () => {
  it("gates the page behind the dashboard:view permission", () => {
    useAuthMock.mockReturnValue({ user: { permissions: [] } });
    renderClient();

    expect(screen.getByText("You do not have access to the dashboard")).toBeTruthy();
    expect(snapshot).not.toHaveBeenCalled();
  });

  it("loads the snapshot for the default week window", async () => {
    renderClient();

    await waitFor(() =>
      expect(snapshot).toHaveBeenCalledWith(expect.objectContaining({ preset: "this_week" })),
    );
    expect(await screen.findByText("Today's sales")).toBeTruthy();
    expect(screen.getByText("Top-selling products")).toBeTruthy();
    expect(screen.getByText("Outstanding due")).toBeTruthy();
  });
});
