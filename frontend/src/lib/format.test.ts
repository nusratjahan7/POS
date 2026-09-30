import { describe, expect, it } from "vitest";

import { formatAmount, formatMoney } from "./format";

describe("formatAmount", () => {
  it("drops a zero cents part but keeps real cents", () => {
    expect(formatAmount("550.00")).toBe("550");
    expect(formatAmount(0)).toBe("0");
    expect(formatAmount("19.80")).toBe("19.80");
    expect(formatAmount("5.2")).toBe("5.20");
  });

  it("falls back to an em dash for missing or invalid values", () => {
    expect(formatAmount(null)).toBe("—");
    expect(formatAmount("")).toBe("—");
    expect(formatAmount("nope")).toBe("—");
  });
});

describe("formatMoney", () => {
  it("drops a zero cents part but keeps real cents", () => {
    expect(formatMoney("4550.00", "USD")).toBe("$4,550");
    expect(formatMoney("227.50", "USD")).toBe("$227.50");
    expect(formatMoney("19.80", "USD")).toBe("$19.80");
    expect(formatMoney(0, "USD")).toBe("$0");
  });

  it("falls back to an em dash for missing or invalid values", () => {
    expect(formatMoney(null)).toBe("—");
    expect(formatMoney("")).toBe("—");
    expect(formatMoney("nope")).toBe("—");
  });
});
