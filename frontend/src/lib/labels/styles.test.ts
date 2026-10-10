import { describe, expect, it } from "vitest";

import { A4_LABEL, THERMAL_LABEL, labelCss } from "./styles";

describe("labelCss", () => {
  it("sizes the thermal roll and breaks a page per label", () => {
    const css = labelCss("thermal");

    expect(css).toContain("size: 50mm 25mm");
    expect(css).toContain("break-after: page");
    expect(THERMAL_LABEL).toEqual({ widthMm: 50, heightMm: 25 });
  });

  it("lays the A4 sheet out as a 3-column grid of 63.5mm labels", () => {
    const css = labelCss("a4");

    expect(css).toContain("size: A4");
    expect(css).toContain("repeat(3, 63.5mm)");
    expect(css).toContain("38.1mm");
    expect(A4_LABEL.perPage).toBe(24);
  });

  it("omits @page rules for the on-screen preview", () => {
    expect(labelCss("a4", { print: false })).not.toContain("@page");
  });
});
