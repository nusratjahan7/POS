import { describe, expect, it } from "vitest";

import { code128Bars } from "./barcode";

describe("code128Bars", () => {
  it("emits start, data, checksum and stop symbols", () => {
    const { bars, moduleCount } = code128Bars("A");

    // Start B + one data symbol + checksum = 3×11 modules, plus the 13-module stop.
    expect(moduleCount).toBe(46);
    expect(bars).toHaveLength(13);
    expect(bars[0]).toEqual({ x: 0, width: 2 });
  });

  it("grows with the payload length", () => {
    expect(code128Bars("AB").moduleCount).toBe(57);
  });

  it("rejects characters outside the Code 128B range", () => {
    expect(() => code128Bars("é")).toThrow(/cannot encode/);
  });
});
