import type * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { NotificationsClient } from "./notifications-client";

const { list, markRead, markAllRead, unreadCount } = vi.hoisted(() => ({
  list: vi.fn(),
  markRead: vi.fn(),
  markAllRead: vi.fn(),
  unreadCount: vi.fn(),
}));

vi.mock("@/lib/api/notifications", () => ({
  notificationsApi: { list, markRead, markAllRead, unreadCount },
}));

vi.mock("@/components/auth/can", () => ({ useCan: () => true }));

// The type filter's Radix Select needs layout APIs jsdom lacks.
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

const unreadNotification = {
  id: "n1",
  type: "low_stock",
  severity: "warning",
  title: "Low stock: Beans",
  body: "Beans (BEAN-1) is down to 2.",
  entity_type: "product",
  entity_id: "p1",
  data: null,
  read_at: null,
  created_at: "2026-10-10T09:00:00Z",
};

function renderClient() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <NotificationsClient />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  list.mockResolvedValue({
    items: [unreadNotification],
    total: 1,
    page: 1,
    page_size: 20,
    pages: 1,
  });
  markRead.mockResolvedValue({ ...unreadNotification, read_at: "2026-10-10T10:00:00Z" });
  markAllRead.mockResolvedValue({ unread: 0 });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("NotificationsClient", () => {
  it("lists notifications", async () => {
    renderClient();
    expect(await screen.findByText("Low stock: Beans")).toBeTruthy();
    expect(screen.getByText("1 total")).toBeTruthy();
  });

  it("marks a single notification as read", async () => {
    const user = userEvent.setup();
    renderClient();

    await user.click(await screen.findByRole("button", { name: "Mark read" }));
    await waitFor(() => expect(markRead).toHaveBeenCalledWith("n1", expect.anything()));
  });

  it("marks every notification as read", async () => {
    const user = userEvent.setup();
    renderClient();

    await user.click(await screen.findByRole("button", { name: /Mark all as read/ }));
    await waitFor(() => expect(markAllRead).toHaveBeenCalled());
  });
});
