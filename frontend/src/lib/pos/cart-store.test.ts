import { beforeEach, describe, expect, it } from "vitest";

import { useCartStore } from "./cart-store";

const base = { name: "Widget", sku: "W-1", unit: "pc", unitPrice: 10 };

function line(productId: string, limit: number) {
  return { ...base, productId, limit };
}

beforeEach(() => {
  useCartStore.setState({
    branchId: null,
    customer: null,
    lines: [],
    orderDiscount: 0,
    held: [],
  });
});

describe("cart stock cap", () => {
  it("adds repeatedly up to the limit", () => {
    for (let index = 0; index < 5; index += 1) {
      expect(useCartStore.getState().addLine(line("p1", 5))).toEqual({ ok: true });
    }
    expect(useCartStore.getState().lines[0].quantity).toBe(5);
  });

  it("blocks going over the limit and leaves the cart untouched", () => {
    for (let index = 0; index < 5; index += 1) useCartStore.getState().addLine(line("p1", 5));

    const result = useCartStore.getState().addLine(line("p1", 5));

    expect(result).toEqual({ ok: false, reason: "limit", available: 5 });
    expect(useCartStore.getState().lines[0].quantity).toBe(5);
  });

  it("refuses a product with no stock at the branch", () => {
    const result = useCartStore.getState().addLine(line("p1", 0));

    expect(result).toEqual({ ok: false, reason: "out_of_stock", available: 0 });
    expect(useCartStore.getState().lines).toHaveLength(0);
  });

  it("clamps a manual quantity to the limit", () => {
    useCartStore.getState().addLine(line("p1", 3));

    const result = useCartStore.getState().setQuantity("p1", 99);

    expect(result).toEqual({ ok: true, clamped: true, quantity: 3 });
    expect(useCartStore.getState().lines[0].quantity).toBe(3);
  });

  it("re-caps lines on a branch switch and drops lines with no stock there", () => {
    useCartStore.getState().addLine(line("p1", 8), 8);
    useCartStore.getState().addLine(line("p2", 4), 2);

    const report = useCartStore.getState().syncLimits({ p1: 5, p2: 0 });

    expect(report.adjusted).toEqual([
      { productId: "p1", name: "Widget", from: 8, to: 5 },
      { productId: "p2", name: "Widget", from: 2, to: 0 },
    ]);
    expect(report.removed).toEqual(["p2"]);
    const lines = useCartStore.getState().lines;
    expect(lines).toHaveLength(1);
    expect(lines[0]).toMatchObject({ productId: "p1", quantity: 5, limit: 5 });
  });
});
