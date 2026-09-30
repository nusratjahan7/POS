import type * as React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { LedgerDialog } from "./ledger-dialog";
import type { LedgerStatement } from "@/lib/api/ledger";

vi.mock("@/lib/api/settings", () => ({
  businessApi: { get: vi.fn().mockResolvedValue({ currency: "USD" }) },
}));

// HeroUI's date-range control needs layout APIs jsdom lacks; the dialog's own
// behaviour is what matters here.
vi.mock("@/app/(dashboard)/sales/sales-date-range", () => ({
  SalesDateRange: () => <div data-testid="date-range" />,
}));

vi.mock("@radix-ui/react-dialog", () => {
  const Pass = ({ children }: { children?: React.ReactNode }) => <>{children}</>;
  return {
    Root: Pass,
    Trigger: Pass,
    Portal: Pass,
    Overlay: () => null,
    Content: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
    Title: ({ children }: { children?: React.ReactNode }) => <h2>{children}</h2>,
    Description: ({ children }: { children?: React.ReactNode }) => <p>{children}</p>,
    Close: Pass,
  };
});

const statement: LedgerStatement = {
  opening_balance: "0.00",
  closing_balance: "4.00",
  entries: [
    {
      occurred_at: "2026-09-29T10:00:00Z",
      entry_type: "sale",
      reference: "INV-1",
      description: "Sale on account",
      debit: "6.00",
      credit: "0.00",
      balance: "6.00",
    },
    {
      occurred_at: "2026-09-30T11:00:00Z",
      entry_type: "payment",
      reference: "REF-9",
      description: "cash",
      debit: "0.00",
      credit: "2.00",
      balance: "4.00",
    },
  ],
};

function renderDialog(fetchStatement: () => Promise<LedgerStatement>) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <LedgerDialog
        title="Jane Doe — account statement"
        description="A statement."
        cacheKey="customer:1"
        fetchStatement={fetchStatement}
        onClose={vi.fn()}
      />
    </QueryClientProvider>,
  );
}

afterEach(cleanup);

describe("LedgerDialog", () => {
  it("renders each entry with its debit, credit and running balance", async () => {
    renderDialog(async () => statement);

    expect(await screen.findByText("INV-1")).toBeTruthy();
    expect(screen.getByText("REF-9")).toBeTruthy();
    expect(screen.getAllByText("$6.00").length).toBeGreaterThanOrEqual(1); // the sale's debit
    expect(screen.getAllByText("$2.00").length).toBeGreaterThanOrEqual(1); // the payment's credit
    // $4.00 is both the payment's balance and the closing balance.
    expect(screen.getAllByText("$4.00").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Closing balance")).toBeTruthy();
  });

  it("says so when the period has no activity", async () => {
    renderDialog(async () => ({
      opening_balance: "0.00",
      closing_balance: "0.00",
      entries: [],
    }));

    expect(await screen.findByText("No account activity for this period.")).toBeTruthy();
  });
});
