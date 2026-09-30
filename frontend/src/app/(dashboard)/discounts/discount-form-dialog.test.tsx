import type * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { DiscountFormDialog } from "./discount-form-dialog";
import type { Discount } from "@/lib/api/discounts";

const { createDiscount, updateDiscount, toastSuccess, toastError } = vi.hoisted(() => ({
  createDiscount: vi.fn(),
  updateDiscount: vi.fn(),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}));

vi.mock("sonner", () => ({ toast: { success: toastSuccess, error: toastError } }));

vi.mock("@/lib/api/discounts", () => ({
  discountsApi: { create: createDiscount, update: updateDiscount },
}));

vi.mock("@/lib/api/catalog", () => ({
  categoriesApi: { options: vi.fn().mockResolvedValue([{ id: "cat-1", name: "Drinks" }]) },
  brandsApi: { options: vi.fn().mockResolvedValue([{ id: "brand-1", name: "Acme" }]) },
}));

vi.mock("@/lib/api/products", () => ({
  productsApi: {
    list: vi.fn().mockResolvedValue({ items: [{ id: "p-1", name: "Cola" }] }),
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

// Radix's checkbox measures itself with ResizeObserver, which jsdom lacks.
class ResizeObserverStub {
  observe() {
    return undefined;
  }
  unobserve() {
    return undefined;
  }
  disconnect() {
    return undefined;
  }
}
vi.stubGlobal("ResizeObserver", ResizeObserverStub);

const existing: Discount = {
  id: "disc-1",
  name: "Ten off",
  code: "TEN",
  scope: "cart",
  type: "percentage",
  value: "10",
  min_order_amount: "0",
  max_discount_amount: null,
  starts_at: null,
  expires_at: null,
  usage_limit: null,
  per_customer_limit: null,
  is_active: true,
  first_order_only: false,
  exclude_discounted: false,
  free_shipping: false,
  product_ids: [],
  category_ids: [],
  brand_ids: [],
  redeemed_count: 0,
  created_at: "2026-09-30T00:00:00Z",
  updated_at: "2026-09-30T00:00:00Z",
};

function renderDialog(discount: Discount | null = null) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onClose = vi.fn();
  const onSaved = vi.fn();
  render(
    <QueryClientProvider client={client}>
      <DiscountFormDialog discount={discount} onClose={onClose} onSaved={onSaved} />
    </QueryClientProvider>,
  );
  return { onClose, onSaved };
}

beforeEach(() => {
  createDiscount.mockResolvedValue(existing);
  updateDiscount.mockResolvedValue(existing);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("DiscountFormDialog", () => {
  it("renders the discount fields", () => {
    renderDialog();

    expect(screen.getByLabelText("Name")).toBeTruthy();
    expect(screen.getByLabelText("Coupon code")).toBeTruthy();
    expect(screen.getByLabelText("Value (%)")).toBeTruthy();
    expect(screen.getByText("Applies to")).toBeTruthy();
    expect(screen.getByText("Type")).toBeTruthy();
  });

  it("requires a name before saving", async () => {
    const user = userEvent.setup();
    renderDialog();

    await user.click(screen.getByRole("button", { name: "Create discount" }));

    expect(await screen.findByText("Give the discount a name.")).toBeTruthy();
    expect(createDiscount).not.toHaveBeenCalled();
  });

  it("rejects a value that is not money", async () => {
    const user = userEvent.setup();
    renderDialog();

    await user.type(screen.getByLabelText("Name"), "Weekly");
    await user.clear(screen.getByLabelText("Value (%)"));
    await user.type(screen.getByLabelText("Value (%)"), "abc");
    await user.click(screen.getByRole("button", { name: "Create discount" }));

    expect(await screen.findByText("Enter a value like 10 or 10.50.")).toBeTruthy();
    expect(createDiscount).not.toHaveBeenCalled();
  });

  it("creates a discount and closes", async () => {
    const user = userEvent.setup();
    const { onSaved, onClose } = renderDialog();

    await user.type(screen.getByLabelText("Name"), "Weekly");
    await user.type(screen.getByLabelText("Coupon code"), "save10");
    await user.click(screen.getByRole("button", { name: "Create discount" }));

    await waitFor(() =>
      expect(createDiscount).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Weekly",
          code: "save10",
          scope: "cart",
          type: "percentage",
          value: "10",
        }),
      ),
    );
    expect(toastSuccess).toHaveBeenCalled();
    expect(onSaved).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it("updates the discount it was opened with", async () => {
    const user = userEvent.setup();
    renderDialog(existing);

    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() =>
      expect(updateDiscount).toHaveBeenCalledWith(
        "disc-1",
        expect.objectContaining({ name: "Ten off", code: "TEN" }),
      ),
    );
  });
});
