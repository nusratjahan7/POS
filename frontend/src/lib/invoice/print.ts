import { invoiceCss, type InvoiceVariant } from "@/lib/invoice/styles";
import { buildPrintDocument, printHtml } from "@/lib/printing/print-html";

/**
 * Wrap rendered invoice markup in a complete, standalone HTML document.
 *
 * Thin wrapper over the shared printer so the invoice keeps its own signature and
 * stylesheet. Pure and DOM-free so it can be asserted in tests.
 */
export function buildInvoiceDocument(
  innerHtml: string,
  options: { title: string; variant: InvoiceVariant },
): string {
  return buildPrintDocument(innerHtml, {
    title: options.title,
    css: invoiceCss(options.variant),
    bodyClass: "inv-doc",
  });
}

/** Print the given invoice markup through the browser. */
export function printInvoice(
  innerHtml: string,
  options: { title: string; variant: InvoiceVariant },
): void {
  printHtml(innerHtml, {
    title: options.title,
    css: invoiceCss(options.variant),
    bodyClass: "inv-doc",
  });
}
