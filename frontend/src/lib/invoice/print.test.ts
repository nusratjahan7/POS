import { describe, expect, it } from "vitest";

import { buildInvoiceDocument } from "./print";

describe("buildInvoiceDocument", () => {
  it("wraps the markup in a standalone document with the invoice styles", () => {
    const html = buildInvoiceDocument('<div class="inv">hi</div>', {
      title: "INV-1",
      variant: "a4",
    });

    expect(html).toContain("<!doctype html>");
    expect(html).toContain('<body class="inv-doc">');
    expect(html).toContain('<div class="inv">hi</div>');
    expect(html).toContain("<title>INV-1</title>");
    expect(html).toContain(".inv-items");
  });

  it("uses the A4 page size for the invoice layout", () => {
    const html = buildInvoiceDocument("", { title: "t", variant: "a4" });
    expect(html).toContain("size: A4");
  });

  it("uses the thermal paper width for the receipt layout", () => {
    const html = buildInvoiceDocument("", { title: "t", variant: "thermal" });
    expect(html).toContain("80mm");
  });

  it("escapes the document title", () => {
    const html = buildInvoiceDocument("", { title: '<img src=x onerror="x">', variant: "a4" });

    expect(html).not.toContain('<img src=x onerror="x">');
    expect(html).toContain("&lt;img src=x onerror=&quot;x&quot;&gt;");
  });
});
