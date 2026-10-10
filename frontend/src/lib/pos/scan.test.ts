import { describe, expect, it } from "vitest";

import type { PosProduct } from "@/lib/api/pos";
import { findExactMatch } from "./scan";

function product(overrides: Partial<PosProduct>): PosProduct {
  return {
    id: "p1",
    name: "Espresso Beans",
    sku: "BEAN-1",
    barcode: "4006381333931",
    unit: "unit",
    selling_price: "2.00",
    discount_price: null,
    image_url: null,
    category_id: null,
    stock_quantity: "10",
    stock_status: "in_stock",
    ...overrides,
  };
}

describe("findExactMatch", () => {
  const products = [
    product({ id: "p1", sku: "BEAN-1", barcode: "4006381333931" }),
    product({ id: "p2", name: "Beans Large", sku: "BEAN-10", barcode: null }),
  ];

  it("matches an exact barcode", () => {
    expect(findExactMatch(products, "4006381333931")?.id).toBe("p1");
  });

  it("matches an exact SKU, case-insensitively", () => {
    expect(findExactMatch(products, "bean-10")?.id).toBe("p2");
  });

  it("trims surrounding whitespace a scanner may add", () => {
    expect(findExactMatch(products, "  4006381333931 ")?.id).toBe("p1");
  });

  it("does not match a substring", () => {
    expect(findExactMatch(products, "BEAN")).toBeUndefined();
    expect(findExactMatch(products, "400638")).toBeUndefined();
  });

  it("returns undefined for an empty term or a product without a barcode", () => {
    expect(findExactMatch(products, "   ")).toBeUndefined();
    expect(findExactMatch(products, "NOPE-1")).toBeUndefined();
  });
});
