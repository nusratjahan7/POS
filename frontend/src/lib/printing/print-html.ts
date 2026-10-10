/**
 * Shared HTML printing.
 *
 * A printable document is a complete, standalone HTML page — markup plus its own
 * embedded stylesheet — so the paper never depends on the app's CSS. It is sent to
 * the printer through a hidden same-document iframe: the browser gets a real,
 * laid-out document to print or "Save as PDF" (crisp, selectable text, never a
 * screenshot), and `window.open` is avoided so a pop-up blocker can't stop it.
 *
 * Invoices and barcode labels both build on this; each supplies its own stylesheet.
 */

function escapeHtml(value: string): string {
  return value.replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] ?? char,
  );
}

export type PrintDocumentOptions = {
  /** The window/PDF title. */
  title: string;
  /** Self-contained stylesheet embedded into the document. */
  css: string;
  /** Optional class on `<body>` (e.g. `inv-doc`). */
  bodyClass?: string;
};

/**
 * Wrap rendered markup in a complete, standalone HTML document.
 *
 * Pure and DOM-free so it can be asserted in tests.
 */
export function buildPrintDocument(innerHtml: string, options: PrintDocumentOptions): string {
  const bodyClass = options.bodyClass ? ` class="${options.bodyClass}"` : "";
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${escapeHtml(options.title)}</title>
    <style>${options.css}</style>
  </head>
  <body${bodyClass}>${innerHtml}</body>
</html>`;
}

/** Wait for images and web fonts, then a frame, so nothing prints blank. */
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
 * Print the given markup through the browser.
 *
 * The document is loaded into a hidden same-document iframe and the iframe's own
 * `print()` is called. The iframe is removed once the dialog has been handed the page.
 */
export function printHtml(innerHtml: string, options: PrintDocumentOptions): void {
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

  frame.srcdoc = buildPrintDocument(innerHtml, options);
  document.body.appendChild(frame);
}
