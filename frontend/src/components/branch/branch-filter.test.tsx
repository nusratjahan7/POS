import type * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { BranchFilter } from "./branch-filter";

const { optionsMock, useAuthMock } = vi.hoisted(() => ({
  optionsMock: vi.fn(),
  useAuthMock: vi.fn(),
}));

vi.mock("@/components/auth/auth-provider", () => ({ useAuth: () => useAuthMock() }));
vi.mock("@/lib/api/rbac", () => ({ branchesApi: { options: optionsMock } }));

// Radix Select needs real layout APIs jsdom lacks; render its parts inline.
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

const MAIN = { id: "b-main", name: "Main Branch", code: "MAIN" };
const OTHER = { id: "b-other", name: "Other Branch", code: "OTHER" };

function renderFilter() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <BranchFilter value="all" onValueChange={() => {}} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  optionsMock.mockResolvedValue([]);
  useAuthMock.mockReturnValue({ user: { all_branches: false, branches: [] } });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("BranchFilter", () => {
  it("offers 'All branches' plus every branch to an administrator", async () => {
    useAuthMock.mockReturnValue({ user: { all_branches: true, branches: [] } });
    optionsMock.mockResolvedValue([MAIN, OTHER]);
    renderFilter();

    expect(await screen.findByText("All branches")).toBeTruthy();
    expect(await screen.findByText("Main Branch")).toBeTruthy();
    expect(screen.getByText("Other Branch")).toBeTruthy();
  });

  it("does not offer 'All branches' to a restricted user", async () => {
    optionsMock.mockResolvedValue([MAIN, OTHER]);
    renderFilter();

    expect(await screen.findByText("Main Branch")).toBeTruthy();
    expect(screen.queryByText("All branches")).toBeNull();
  });

  it("renders nothing for a single-branch user", async () => {
    optionsMock.mockResolvedValue([MAIN]);
    renderFilter();

    await waitFor(() => expect(optionsMock).toHaveBeenCalled());
    expect(screen.queryByLabelText("Filter by branch")).toBeNull();
    expect(screen.queryByText("Main Branch")).toBeNull();
  });
});
