import type * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { PosPaymentDialog } from "./pos-payment-dialog";
import type { PriceBreakdown } from "@/lib/api/discounts";
import type { CartLine, CartTotals } from "@/lib/pos/cart-store";

const { validate, createSale, toastError } = vi.hoisted(() => ({
  validate: vi.fn(),
  createSale: vi.fn(),
  toastError: vi.fn(),
}));

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: toastError } }));

vi.mock("@/lib/api/discounts", () => ({ discountsApi: { validate } }));

vi.mock("@/lib/api/sales", () => ({ salesApi: { create: createSale } }));

vi.mock("@/lib/api/settings", () => ({
  paymentMethodsApi: {
    options: vi.fn().mockResolvedValue([
      {
        id: "m-cash",
        name: "Cash",
        code: "CASH",
        kind: "cash",
        opens_cash_drawer: true,
        requires_reference: false,
      },
    ]),
  },
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

const lines: CartLine[] = [
  {
    productId: "p-1",
    name: "Beans",
    sku: "BEAN-1",
    unit: "pc",
    unitPrice: 2,
    quantity: 3,
    discount: 0,
    limit: 20,
  },
];

const totals: CartTotals = {
  subtotal: 6,
  lineDiscounts: 0,
  discountTotal: 1,
  net: 5,
  tax: 0,
  total: 5,
  itemCount: 3,
};

const breakdown: PriceBreakdown = {
  lines: [],
  subtotal: "6.00",
  line_discounts: "0.00",
  automatic_discount: "0.00",
  coupon_discount: "1.00",
  order_discount: "0.00",
  total_discount: "1.00",
  net: "5.00",
  coupon: { code: "SAVE1", name: "Save one", amount: "1.00" },
  applied: [{ code: "SAVE1", name: "Save one", amount: "1.00" }],
};

function renderDialog(couponCode = "") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onClose = vi.fn();
  const onComplete = vi.fn();
  const onCouponChange = vi.fn();
  render(
    <QueryClientProvider client={client}>
      <PosPaymentDialog
        lines={lines}
        totals={totals}
        orderDiscount={0}
        customer={null}
        branchId="b-1"
        registerId="r-1"
        couponCode={couponCode}
        onCouponChange={onCouponChange}
        currency="USD"
        onClose={onClose}
        onComplete={onComplete}
      />
    </QueryClientProvider>,
  );
  return { onClose, onComplete, onCouponChange };
}

beforeEach(() => {
  validate.mockResolvedValue(breakdown);
  createSale.mockResolvedValue({});
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("PosPaymentDialog coupon preview", () => {
  it("asks the server to price the cart and shows the breakdown", async () => {
    renderDialog("SAVE1");

    await waitFor(() =>
      expect(validate).toHaveBeenCalledWith(
        expect.objectContaining({
          coupon_code: "SAVE1",
          items: [{ product_id: "p-1", quantity: "3", discount: "0.00" }],
        }),
      ),
    );

    expect(await screen.findByText(/Save one/)).toBeTruthy();
    expect(screen.getByText("Discount total")).toBeTruthy();
    expect(screen.getAllByText(/1\.00/).length).toBeGreaterThanOrEqual(1);
  });

  it("says so when no discounts apply", async () => {
    validate.mockResolvedValue({
      ...breakdown,
      coupon: null,
      coupon_discount: "0.00",
      total_discount: "0.00",
      applied: [],
    });

    renderDialog();

    expect(await screen.findByText("No discounts apply to this cart.")).toBeTruthy();
  });

  it("uppercases the coupon code as it is typed", async () => {
    const user = userEvent.setup();
    const { onCouponChange } = renderDialog();

    await user.type(screen.getByLabelText("Coupon code"), "a");

    expect(onCouponChange).toHaveBeenCalledWith("A");
  });

  it("clears the coupon", async () => {
    const user = userEvent.setup();
    const { onCouponChange } = renderDialog("SAVE1");

    await user.click(screen.getByRole("button", { name: "Clear" }));

    expect(onCouponChange).toHaveBeenCalledWith("");
  });
});
