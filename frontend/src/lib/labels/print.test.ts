import { describe, expect, it } from "vitest";

import { buildLabelDocument } from "./print";

describe("buildLabelDocument", () => {
  it("wraps label markup in a standalone document with the label styles", () => {
    const html = buildLabelDocument('<div class="lbl-sheet"></div>', "a4");

    expect(html).toContain("<!doctype html>");
    expect(html).toContain('<body class="lbl-doc">');
    expect(html).toContain('<div class="lbl-sheet"></div>');
    expect(html).toContain("size: A4");
    expect(html).toContain(".lbl-name");
  });

  it("uses the thermal page size for the roll layout", () => {
    expect(buildLabelDocument("", "thermal")).toContain("50mm 25mm");
  });
});
