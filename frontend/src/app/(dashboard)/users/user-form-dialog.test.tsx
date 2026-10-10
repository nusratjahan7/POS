import type * as React from "react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { UserFormDialog } from "./user-form-dialog";

// Radix Checkbox measures its box with a ResizeObserver, which jsdom lacks.
beforeAll(() => {
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
});

const { updateMock } = vi.hoisted(() => ({ updateMock: vi.fn() }));

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/lib/api/rbac", () => ({
  usersApi: { update: updateMock, create: vi.fn() },
}));
vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {
    fieldErrors: Record<string, string> = {};
  },
  describeError: () => "Something went wrong",
}));

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

const managed = {
  id: "u1",
  email: "scoped@example.com",
  full_name: "Scoped Manager",
  phone: null,
  is_active: true,
  is_superuser: false,
  last_login_at: null,
  branch: MAIN,
  branches: [MAIN],
  roles: [],
  created_at: "2026-01-01T00:00:00Z",
};

beforeEach(() => {
  updateMock.mockResolvedValue(managed);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("UserFormDialog", () => {
  it("submits the assigned branches and the primary branch", async () => {
    const user = userEvent.setup();
    render(
      <UserFormDialog
        user={managed}
        roles={[]}
        branches={[MAIN, OTHER]}
        onClose={() => {}}
        onSaved={() => {}}
      />,
    );

    // Reassign: drop Main, add Other.
    await user.click(screen.getByRole("checkbox", { name: /Main Branch/ }));
    await user.click(screen.getByRole("checkbox", { name: /Other Branch/ }));
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => expect(updateMock).toHaveBeenCalled());
    expect(updateMock.mock.calls[0][0]).toBe("u1");
    expect(updateMock.mock.calls[0][1]).toMatchObject({
      branch_id: "b-main",
      branch_ids: ["b-other"],
    });
  });
});
