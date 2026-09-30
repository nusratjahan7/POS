import type * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { SupplierPaymentDialog } from "./supplier-payment-dialog";
import type { Supplier } from "@/lib/api/suppliers";

const { recordPayment, toastSuccess, toastError } = vi.hoisted(() => ({
  recordPayment: vi.fn(),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}));

vi.mock("sonner", () => ({ toast: { success: toastSuccess, error: toastError } }));

vi.mock("@/lib/api/suppliers", () => ({
  suppliersApi: { recordPayment },
}));

vi.mock("@/lib/api/settings", () => ({
  businessApi: { get: vi.fn().mockResolvedValue({ currency: "USD" }) },
  paymentMethodsApi: { options: vi.fn().mockResolvedValue([]) },
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

const supplier = { id: "supplier-1", name: "Acme Supply", balance: "30.00" } as Supplier;

function renderDialog() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onClose = vi.fn();
  const onPaid = vi.fn();
  render(
    <QueryClientProvider client={client}>
      <SupplierPaymentDialog supplier={supplier} onClose={onClose} onPaid={onPaid} />
    </QueryClientProvider>,
  );
  return { onClose, onPaid };
}

beforeEach(() => {
  recordPayment.mockResolvedValue({ id: "payment-1" });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("SupplierPaymentDialog", () => {
  it("refuses a payment larger than the outstanding balance", async () => {
    const user = userEvent.setup();
    renderDialog();

    await user.type(screen.getByLabelText("Amount"), "40");
    await user.click(screen.getByRole("button", { name: "Record payment" }));

    expect(
      await screen.findByText("The payment cannot exceed the outstanding balance."),
    ).toBeTruthy();
    expect(recordPayment).not.toHaveBeenCalled();
  });

  it("records a valid payment and reports it", async () => {
    const user = userEvent.setup();
    const { onPaid, onClose } = renderDialog();

    await user.type(screen.getByLabelText("Amount"), "10");
    await user.click(screen.getByRole("button", { name: "Record payment" }));

    await waitFor(() =>
      expect(recordPayment).toHaveBeenCalledWith("supplier-1", {
        amount: "10",
        method: null,
        reference: null,
        note: null,
      }),
    );
    expect(toastSuccess).toHaveBeenCalled();
    expect(onPaid).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });
});
