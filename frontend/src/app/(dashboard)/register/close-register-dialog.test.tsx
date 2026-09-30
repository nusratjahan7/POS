import type * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { CloseRegisterDialog } from "./close-register-dialog";
import type { RegisterSessionDetail } from "@/lib/api/register-sessions";

const { closeSession, toastSuccess, toastError } = vi.hoisted(() => ({
  closeSession: vi.fn(),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}));

vi.mock("sonner", () => ({ toast: { success: toastSuccess, error: toastError } }));

vi.mock("@/lib/api/register-sessions", () => ({
  registerSessionsApi: { close: closeSession },
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

const detail: RegisterSessionDetail = {
  session: {
    id: "session-1",
    register: { id: "register-1", name: "Front Counter" },
    branch: { id: "branch-1", name: "Main Branch", code: "MAIN" },
    opening_cash: "100.00",
    status: "open",
    opened_by: null,
    opened_at: "2026-09-30T09:00:00Z",
    closed_by: null,
    closed_at: null,
    expected_cash: "121.00",
    actual_cash: null,
    difference: null,
    closing_note: null,
  },
  summary: {
    opening_cash: "100.00",
    cash_sales: "6.00",
    cash_refunds: "0.00",
    cash_expenses: "0.00",
    cash_in: "20.00",
    cash_out: "5.00",
    expected_cash: "121.00",
    movements: [],
  },
};

function renderDialog() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onClose = vi.fn();
  const onClosed = vi.fn();
  render(
    <QueryClientProvider client={client}>
      <CloseRegisterDialog
        detail={detail}
        currency="USD"
        onClose={onClose}
        onClosed={onClosed}
      />
    </QueryClientProvider>,
  );
  return { onClose, onClosed };
}

beforeEach(() => {
  closeSession.mockResolvedValue({ session: detail.session, summary: detail.summary });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("CloseRegisterDialog", () => {
  it("shows the reconciliation and the shortfall as cash is counted", async () => {
    const user = userEvent.setup();
    renderDialog();

    expect(screen.getByText("Expected in the drawer")).toBeTruthy();
    expect(screen.getAllByText("$121.00").length).toBeGreaterThanOrEqual(1);

    await user.type(screen.getByLabelText("Counted (actual) cash"), "120");

    expect(await screen.findByText("Short")).toBeTruthy();
    expect(screen.getByText("$1.00")).toBeTruthy();
  });

  it("closes the register with the counted cash", async () => {
    const user = userEvent.setup();
    const { onClosed, onClose } = renderDialog();

    await user.type(screen.getByLabelText("Counted (actual) cash"), "121");
    await user.click(screen.getByRole("button", { name: "Close register" }));

    await waitFor(() =>
      expect(closeSession).toHaveBeenCalledWith("session-1", {
        actual_cash: "121",
        note: null,
      }),
    );
    expect(toastSuccess).toHaveBeenCalled();
    expect(onClosed).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });
});
