import { describe, expect, it } from "vitest";

import { EAN13_MODULE_COUNT, encodeEan13, encodeUpcA, ean13CheckDigit, isValidEan13 } from "./ean";

// Well-known valid samples.
const EAN = "4006381333931";
const UPC = "036000291452";

describe("ean13CheckDigit", () => {
  it("computes the 13th digit", () => {
    expect(ean13CheckDigit("400638133393")).toBe(1);
    expect(ean13CheckDigit("590123412345")).toBe(7);
  });
});

describe("isValidEan13", () => {
  it("accepts a correct check digit and rejects a wrong one", () => {
    expect(isValidEan13(EAN)).toBe(true);
    expect(isValidEan13("4006381333932")).toBe(false);
  });

  it("rejects values that are not exactly 13 digits", () => {
    expect(isValidEan13("40063813339")).toBe(false);
    expect(isValidEan13("40063813339311")).toBe(false);
    expect(isValidEan13("4006381333A31")).toBe(false);
  });
});

describe("encodeEan13", () => {
  it("produces the 95-module symbol with tall guard bars", () => {
    const encoded = encodeEan13(EAN);

    expect(encoded.format).toBe("ean13");
    expect(encoded.moduleCount).toBe(EAN13_MODULE_COUNT);
    expect(encoded.moduleCount).toBe(95);
    expect(encoded.text).toBe(EAN);
    // Left (2), centre (2) and right (2) guard bars are present.
    expect(encoded.bars.filter((bar) => bar.guard)).toHaveLength(6);
  });

  it("refuses a wrong length or a bad check digit", () => {
    expect(() => encodeEan13("12345")).toThrow(/13 digits/);
    expect(() => encodeEan13("4006381333932")).toThrow(/check digit/);
  });
});

describe("encodeUpcA", () => {
  it("encodes a 12-digit value with UPC-A labelling", () => {
    const encoded = encodeUpcA(UPC);

    expect(encoded.format).toBe("upca");
    expect(encoded.text).toBe(UPC);
    expect(encoded.moduleCount).toBe(EAN13_MODULE_COUNT);
  });

  it("rejects a non-12-digit value", () => {
    expect(() => encodeUpcA("123")).toThrow(/12 digits/);
  });
});
