import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { NotificationBell } from "./notification-bell";

const { unreadCount, list, markAllRead, markRead } = vi.hoisted(() => ({
  unreadCount: vi.fn(),
  list: vi.fn(),
  markAllRead: vi.fn(),
  markRead: vi.fn(),
}));

vi.mock("@/lib/api/notifications", () => ({
  notificationsApi: { unreadCount, list, markAllRead, markRead },
}));

function renderBell() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <NotificationBell />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  unreadCount.mockResolvedValue({ unread: 2 });
  list.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 6, pages: 0 });
  markAllRead.mockResolvedValue({ unread: 0 });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("NotificationBell", () => {
  it("shows the unread count on the bell", async () => {
    renderBell();

    await waitFor(() => expect(unreadCount).toHaveBeenCalled());
    expect(await screen.findByLabelText("Notifications, 2 unread")).toBeTruthy();
  });

  it("has a plain label when there is nothing unread", async () => {
    unreadCount.mockResolvedValue({ unread: 0 });
    renderBell();

    expect(await screen.findByLabelText("Notifications")).toBeTruthy();
  });
});
