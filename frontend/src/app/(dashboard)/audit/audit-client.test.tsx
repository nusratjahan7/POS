import type * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AuditClient } from "./audit-client";

const { list } = vi.hoisted(() => ({ list: vi.fn() }));

vi.mock("@/lib/api/audit", () => ({ auditApi: { list } }));

vi.mock("@/components/auth/can", () => ({ useCan: () => true }));

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

const entry = {
  id: "log1",
  user_id: "u1",
  user_email: "admin@example.com",
  user_name: "Test Administrator",
  action: "catalog.product.price_change",
  module: "catalog",
  entity: "product",
  entity_id: "11111111-2222-3333-4444-555555555555",
  old_data: { selling_price: "2.00" },
  new_data: { selling_price: "9.99" },
  ip_address: "203.0.113.7",
  user_agent: "vitest",
  created_at: "2026-10-10T09:00:00Z",
};

function renderClient() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <AuditClient />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  list.mockResolvedValue({ items: [entry], total: 1, page: 1, page_size: 20, pages: 1 });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("AuditClient", () => {
  it("renders audit rows with actor and action", async () => {
    renderClient();

    expect(await screen.findByText("catalog.product.price_change")).toBeTruthy();
    expect(screen.getByText("Test Administrator")).toBeTruthy();
    expect(screen.getByText("203.0.113.7")).toBeTruthy();
  });

  it("opens a detail dialog with the before and after snapshots", async () => {
    const user = userEvent.setup();
    renderClient();

    await user.click(await screen.findByRole("button", { name: "View" }));

    await waitFor(() => expect(screen.getByText("Before")).toBeTruthy());
    expect(screen.getByText("After")).toBeTruthy();
    expect(screen.getByText(/"2.00"/)).toBeTruthy();
    expect(screen.getByText(/"9.99"/)).toBeTruthy();
  });
});
