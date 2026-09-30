import type * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ExpenseFormDialog } from "./expense-form-dialog";

const { createExpense, toastSuccess, toastError } = vi.hoisted(() => ({
  createExpense: vi.fn(),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}));

vi.mock("sonner", () => ({ toast: { success: toastSuccess, error: toastError } }));

vi.mock("@/lib/api/expenses", () => ({
  expenseCategoriesApi: {
    options: vi.fn().mockResolvedValue([{ id: "cat-1", name: "Supplies" }]),
  },
  expensesApi: { create: createExpense },
}));

vi.mock("@/lib/api/rbac", () => ({
  branchesApi: { options: vi.fn().mockResolvedValue([{ id: "b-1", name: "Main", code: "MAIN" }]) },
}));

vi.mock("@/lib/api/settings", () => ({
  paymentMethodsApi: {
    options: vi.fn().mockResolvedValue([
      { id: "m-cash", name: "Cash", code: "CASH", kind: "cash", opens_cash_drawer: true },
    ]),
  },
}));

vi.mock("@/lib/api/register-sessions", () => ({
  registerSessionsApi: { openSessions: vi.fn().mockResolvedValue([]) },
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

function renderDialog() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onClose = vi.fn();
  const onSaved = vi.fn();
  render(
    <QueryClientProvider client={client}>
      <ExpenseFormDialog onClose={onClose} onSaved={onSaved} />
    </QueryClientProvider>,
  );
  return { onClose, onSaved };
}

beforeEach(() => {
  createExpense.mockResolvedValue({ id: "expense-1" });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ExpenseFormDialog", () => {
  it("renders the expense fields", () => {
    renderDialog();

    expect(screen.getByLabelText("Amount")).toBeTruthy();
    expect(screen.getByLabelText("Date")).toBeTruthy();
    expect(screen.getByText("Category")).toBeTruthy();
    expect(screen.getByText("Payment method")).toBeTruthy();
  });

  it("rejects an invalid amount", async () => {
    const user = userEvent.setup();
    renderDialog();

    await user.type(screen.getByLabelText("Amount"), "abc");
    await user.click(screen.getByRole("button", { name: "Record expense" }));

    expect(await screen.findByText("Enter an amount like 100 or 100.50.")).toBeTruthy();
    expect(createExpense).not.toHaveBeenCalled();
  });

  it("requires a payment method before recording", async () => {
    const user = userEvent.setup();
    renderDialog();

    await user.type(screen.getByLabelText("Amount"), "30");
    await user.click(screen.getByRole("button", { name: "Record expense" }));

    expect(
      await screen.findByText("Choose a branch, a category and a payment method."),
    ).toBeTruthy();
    expect(createExpense).not.toHaveBeenCalled();
  });
});
