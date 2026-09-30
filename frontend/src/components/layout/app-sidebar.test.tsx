import type * as React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AppSidebar } from "./app-sidebar";

vi.mock("next/navigation", () => ({ usePathname: () => "/" }));

vi.mock("@/components/auth/auth-provider", () => ({
  useAuth: () => ({ user: { permissions: ["*"] } }),
}));

vi.mock("@/lib/nav", () => ({
  navGroups: [
    {
      label: "Main",
      items: [{ title: "Dashboard", href: "/", icon: () => null, status: "available" }],
    },
  ],
}));

// Radix's tooltip needs layout APIs jsdom lacks; the rail's behaviour is what
// matters here, so the primitives collapse to plain wrappers.
vi.mock("@radix-ui/react-tooltip", () => ({
  Provider: ({ children }: { children: React.ReactNode }) => children,
  Root: ({ children }: { children: React.ReactNode }) => children,
  Trigger: ({ children }: { children: React.ReactNode }) => children,
  Portal: ({ children }: { children: React.ReactNode }) => children,
  Content: () => null,
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("AppSidebar", () => {
  it("shows the wordmark while expanded", () => {
    render(<AppSidebar />);

    expect(screen.getByText("Point of Sale")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Collapse navigation" })).toBeTruthy();
  });

  it("keeps the brand glyph and swaps in the expand control when collapsed", async () => {
    const user = userEvent.setup();
    render(<AppSidebar />);

    await user.click(screen.getByRole("button", { name: "Collapse navigation" }));

    // The wordmark cannot fit the rail; the glyph remains as the brand mark.
    expect(screen.queryByText("Point of Sale")).toBeNull();
    expect(screen.getByRole("button", { name: "Expand navigation" })).toBeTruthy();
  });
});
