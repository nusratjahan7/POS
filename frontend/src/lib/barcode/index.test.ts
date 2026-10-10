import { describe, expect, it } from "vitest";

import { code128Bars, detectFormat, encodeBarcode } from "./index";

describe("detectFormat", () => {
  it("picks EAN-13 for a valid 13-digit number", () => {
    expect(detectFormat("4006381333931")).toBe("ean13");
  });

  it("picks UPC-A for a 12-digit number", () => {
    expect(detectFormat("036000291452")).toBe("upca");
  });

  it("falls back to Code 128 for anything else", () => {
    expect(detectFormat("BEAN-1KG")).toBe("code128");
    expect(detectFormat("4006381333932")).toBe("code128"); // bad EAN check digit
    expect(detectFormat("1234")).toBe("code128");
  });
});

describe("encodeBarcode", () => {
  it("auto-detects the symbology", () => {
    expect(encodeBarcode("4006381333931").format).toBe("ean13");
    expect(encodeBarcode("036000291452").format).toBe("upca");
    expect(encodeBarcode("INV-20260101-AB").format).toBe("code128");
  });

  it("honours an explicit format", () => {
    expect(encodeBarcode("4006381333931", "ean13").format).toBe("ean13");
  });

  it("falls back to Code 128 when a retail format cannot encode the value", () => {
    expect(encodeBarcode("ABC", "ean13").format).toBe("code128");
    expect(encodeBarcode("123", "upca").format).toBe("code128");
  });

  it("throws only when nothing can encode the value", () => {
    expect(() => encodeBarcode("")).toThrow(/required/);
    expect(() => encodeBarcode("café")).toThrow(/cannot encode/);
  });
});

describe("compatibility re-exports", () => {
  it("still exposes code128Bars", () => {
    expect(code128Bars("A").moduleCount).toBe(46);
  });
});
