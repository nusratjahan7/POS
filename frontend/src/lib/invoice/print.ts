import { invoiceCss, type InvoiceVariant } from "@/lib/invoice/styles";

/** Escape anything that goes into the standalone document's `<title>`. */
function escapeHtml(value: string): string {
  return value.replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] ?? char,
  );
}

/**
 * Wrap rendered invoice markup in a complete, standalone HTML document.
 *
 * Pure and DOM-free so it can be asserted in tests. The stylesheet travels inside
 * the document, so the printed page never depends on the app's own CSS.
 */
export function buildInvoiceDocument(
  innerHtml: string,
  options: { title: string; variant: InvoiceVariant },
): string {
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${escapeHtml(options.title)}</title>
    <style>${invoiceCss(options.variant)}</style>
  </head>
  <body class="inv-doc">${innerHtml}</body>
</html>`;
}

/** Wait for the logo and any web fonts, then a frame, so nothing prints blank. */
async function whenAssetsReady(doc: Document): Promise<void> {
  const images = Array.from(doc.images);
  await Promise.all(
    images.map((image) =>
      image.complete
        ? Promise.resolve()
        : new Promise<void>((resolve) => {
            image.addEventListener("load", () => resolve(), { once: true });
            image.addEventListener("error", () => resolve(), { once: true });
          }),
    ),
  );

  const fonts = (doc as Document & { fonts?: FontFaceSet }).fonts;
  if (fonts) {
    try {
      await fonts.ready;
    } catch {
      // Fonts are best-effort; never block the print dialog on them.
    }
  }

  await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
}

/**
 * Print the given invoice markup through the browser.
 *
 * The markup is loaded into a hidden same-document iframe and the iframe's own
 * `print()` is called. That gives the browser a real, laid-out document to send to
 * the printer or "Save as PDF" — crisp, selectable text, never a screenshot — and
 * it avoids `window.open`, so a pop-up blocker can't stop it. The iframe is removed
 * once the print dialog has been handed the page.
 */
export function printInvoice(
  innerHtml: string,
  options: { title: string; variant: InvoiceVariant },
): void {
  const frame = document.createElement("iframe");
  frame.setAttribute("aria-hidden", "true");
  frame.tabIndex = -1;
  frame.style.cssText =
    "position:fixed;right:0;bottom:0;width:0;height:0;border:0;visibility:hidden;";

  frame.addEventListener(
    "load",
    () => {
      const win = frame.contentWindow;
      const doc = frame.contentDocument;
      if (!win || !doc) {
        frame.remove();
        return;
      }
      void whenAssetsReady(doc).then(() => {
        win.focus();
        win.print();
        window.setTimeout(() => frame.remove(), 1000);
      });
    },
    { once: true },
  );

  frame.srcdoc = buildInvoiceDocument(innerHtml, options);
  document.body.appendChild(frame);
}
