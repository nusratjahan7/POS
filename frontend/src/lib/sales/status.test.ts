import { describe, expect, it } from "vitest";

import { paymentStatusOf } from "./status";

describe("paymentStatusOf", () => {
  it("reads a settled sale as paid", () => {
    expect(paymentStatusOf({ paid: "10.00", due: "0.00" })).toBe("paid");
  });

  it("separates a partly paid sale from a fully unpaid one", () => {
    expect(paymentStatusOf({ paid: "4.00", due: "6.00" })).toBe("partial");
    expect(paymentStatusOf({ paid: "0.00", due: "6.00" })).toBe("unpaid");
  });

  it("treats a fully discounted sale as settled", () => {
    expect(paymentStatusOf({ paid: "0.00", due: "0.00" })).toBe("paid");
  });
});
