/**
 * Print a complete HTML document through a hidden same-document iframe.
 *
 * The report's printable HTML comes from the API (`format=html`), so the layout
 * lives in one place. Loading it into an iframe — rather than `window.open` —
 * gives the browser a real laid-out document to send to the printer or "Save as
 * PDF", and a pop-up blocker cannot stop it.
 */
export function printHtmlDocument(html: string, title = "Report"): void {
  const frame = document.createElement("iframe");
  frame.setAttribute("aria-hidden", "true");
  frame.title = title;
  frame.tabIndex = -1;
  frame.style.cssText =
    "position:fixed;right:0;bottom:0;width:0;height:0;border:0;visibility:hidden;";

  frame.addEventListener(
    "load",
    () => {
      const view = frame.contentWindow;
      if (!view) {
        frame.remove();
        return;
      }
      // One frame so the document is laid out before the dialog opens.
      window.setTimeout(() => {
        view.focus();
        view.print();
        window.setTimeout(() => frame.remove(), 1000);
      }, 100);
    },
    { once: true },
  );

  frame.srcdoc = html;
  document.body.appendChild(frame);
}
