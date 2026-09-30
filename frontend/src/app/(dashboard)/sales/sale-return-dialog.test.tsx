import type * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { SaleReturnDialog } from "./sale-return-dialog";
import type { Sale, SaleReturn } from "@/lib/api/sales";

const { listReturns, createReturn, paymentOptions, toastSuccess, toastError } = vi.hoisted(() => ({
  listReturns: vi.fn(),
  createReturn: vi.fn(),
  paymentOptions: vi.fn(),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}));

vi.mock("sonner", () => ({ toast: { success: toastSuccess, error: toastError } }));

vi.mock("@/lib/api/client", () => ({ describeError: () => "Something went wrong." }));

vi.mock("@/lib/api/sales", () => ({ salesApi: { listReturns, createReturn } }));

vi.mock("@/lib/api/settings", () => ({ paymentMethodsApi: { options: paymentOptions } }));

// Radix's dialog and select need layout APIs jsdom lacks; the dialog's own
// behaviour is what matters here, so the primitives collapse to plain wrappers.
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

function saleFixture(overrides: Partial<Sale> = {}): Sale {
  return {
    id: "sale-1",
    sale_number: "INV-1",
    branch: { id: "branch-1", name: "Main Branch" },
    register_id: null,
    customer: { id: "customer-1", name: "Jane Doe", balance: "6.00" },
    cashier: { id: "user-1", full_name: "Admin" },
    subtotal: "6.00",
    discount: "0.00",
    tax: "0.00",
    total: "6.00",
    paid: "0.00",
    due: "6.00",
    change_amount: "0.00",
    received_amount: "0.00",
    status: "completed",
    note: null,
    items: [
      {
        id: "item-1",
        product_id: "product-1",
        product_name: "Beans",
        sku: "BEAN-1",
        unit: "pcs",
        quantity: "3.000",
        unit_price: "2.00",
        discount: "0.00",
        subtotal: "6.00",
        line_total: "6.00",
      },
    ],
    payments: [],
    sold_at: "2026-09-29T10:00:00Z",
    created_at: "2026-09-29T10:00:00Z",
    returned_amount: "0.00",
    refunded_at: null,
    refunded_by: null,
    refund_reason: null,
    ...overrides,
  };
}

const createdReturn: SaleReturn = {
  id: "return-1",
  return_number: "RET-20260929-ABC123",
  status: "completed",
  reason: null,
  note: null,
  refund_amount: "6.00",
  credit_reversed: "6.00",
  cash_refund: "0.00",
  payment_method: null,
  refund_reference: null,
  created_by: null,
  completed_by: null,
  created_at: "2026-09-29T11:00:00Z",
  completed_at: "2026-09-29T11:00:00Z",
  cancelled_at: null,
  items: [
    {
      id: "return-item-1",
      sale_item_id: "item-1",
      product_id: "product-1",
      product_name: "Beans",
      sku: "BEAN-1",
      quantity: "3.000",
      unit_price: "2.00",
      line_total: "6.00",
    },
  ],
};

function renderDialog(sale: Sale = saleFixture()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onClose = vi.fn();
  const onReturned = vi.fn();
  render(
    <QueryClientProvider client={client}>
      <SaleReturnDialog sale={sale} onClose={onClose} onReturned={onReturned} />
    </QueryClientProvider>,
  );
  return { onClose, onReturned };
}

async function findQuantityInput() {
  return await screen.findByLabelText("Quantity of Beans to return");
}

function confirmButton() {
  return screen.getByRole("button", { name: "Confirm return" }) as HTMLButtonElement;
}

beforeEach(() => {
  listReturns.mockResolvedValue([]);
  paymentOptions.mockResolvedValue([]);
  createReturn.mockResolvedValue(createdReturn);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("SaleReturnDialog", () => {
  it("lists the sale's lines with what can still be returned", async () => {
    renderDialog();
    await findQuantityInput();

    expect(screen.getByText("Beans")).toBeTruthy();
    expect(screen.getByText("Can return")).toBeTruthy();
  });

  it("will not confirm until a quantity is chosen", async () => {
    renderDialog();
    await findQuantityInput();

    expect(confirmButton().disabled).toBe(true);
  });

  it("posts the planned lines and reports the refund", async () => {
    const user = userEvent.setup();
    const { onReturned, onClose } = renderDialog();
    const input = await findQuantityInput();

    await user.type(input, "3");
    await user.click(confirmButton());

    await waitFor(() =>
      expect(createReturn).toHaveBeenCalledWith("sale-1", {
        items: [{ sale_item_id: "item-1", quantity: "3" }],
        reason: null,
        payment_method_id: null,
        reference: null,
      }),
    );
    expect(toastSuccess).toHaveBeenCalled();
    expect(onReturned).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it("asks how a cash refund is settled when money goes back", async () => {
    const user = userEvent.setup();
    renderDialog(saleFixture({ paid: "6.00", due: "0.00", received_amount: "6.00" }));
    const input = await findQuantityInput();

    await user.type(input, "3");

    expect(screen.getByText(/Choose how the cash part of the refund is settled/)).toBeTruthy();
    expect(confirmButton().disabled).toBe(true);
  });
});
