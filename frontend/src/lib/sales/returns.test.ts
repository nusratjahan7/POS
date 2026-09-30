import { describe, expect, it } from "vitest";

import { planReturn, remainingQuantity, splitRefund, type ReturnableLine } from "./returns";

function line(overrides: Partial<ReturnableLine> = {}): ReturnableLine {
  return {
    saleItemId: "line-1",
    productName: "Beans",
    sku: "BEAN-1",
    unitPrice: 2,
    sold: 3,
    returned: 0,
    lineTotal: 6,
    alreadyRefunded: 0,
    ...overrides,
  };
}

describe("remainingQuantity", () => {
  it("subtracts what has already come back", () => {
    expect(remainingQuantity(line({ sold: 3, returned: 2 }))).toBe(1);
    expect(remainingQuantity(line({ sold: 3, returned: 3 }))).toBe(0);
  });
});

describe("planReturn", () => {
  it("refunds a partial quantity proportionally to the line net", () => {
    const { lines, total } = planReturn([line()], { "line-1": 1 }, 6);
    expect(lines).toEqual([{ saleItemId: "line-1", quantity: 1, refund: 2 }]);
    expect(total).toBe(2);
  });

  it("refunds exactly what is left of the line when the rest comes back", () => {
    // Two of three units already returned for 4.00; the last is worth the rest.
    const { total } = planReturn(
      [line({ returned: 2, alreadyRefunded: 4 })],
      { "line-1": 1 },
      6,
    );
    expect(total).toBe(2);
  });

  it("never plans more than is still returnable", () => {
    const { lines } = planReturn([line({ returned: 2 })], { "line-1": 5 }, 6);
    expect(lines[0].quantity).toBe(1);
  });

  it("caps the refund at what the sale still has left", () => {
    // The line's net is 20.00 but the sale only has 15.00 left to give back.
    const { total } = planReturn([line({ sold: 2, lineTotal: 20 })], { "line-1": 2 }, 15);
    expect(total).toBe(15);
  });

  it("ignores lines with nothing selected", () => {
    expect(planReturn([line()], {}, 6).lines).toHaveLength(0);
  });
});

describe("splitRefund", () => {
  it("clears the outstanding balance before paying cash", () => {
    expect(splitRefund(6, 4, 0)).toEqual({ credited: 4, cash: 2 });
  });

  it("pays everything out when nothing is owed", () => {
    expect(splitRefund(6, 0, 0)).toEqual({ credited: 0, cash: 6 });
  });

  it("accounts for debt an earlier return already cleared", () => {
    // The 4.00 due was cleared by the first return, so this one is all cash.
    expect(splitRefund(2, 4, 4)).toEqual({ credited: 0, cash: 2 });
  });
});
