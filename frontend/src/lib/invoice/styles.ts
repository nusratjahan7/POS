/**
 * The invoice's own stylesheet.
 *
 * It is deliberately self-contained — no Tailwind, no app tokens — because it is
 * used in two places: the on-screen preview and a detached print document. Keeping
 * the CSS in one string means the paper copy is exactly what the cashier approved
 * on screen, and nothing from the till's layout can leak onto the paper.
 *
 * `print: false` omits the `@page` rules so an injected `<style>` in the live app
 * document cannot change the paper size of anything else.
 */

export type InvoiceVariant = "thermal" | "a4";

const BASE = `
.inv {
  --inv-ink: #0f172a;
  --inv-muted: #64748b;
  --inv-line: #cbd5e1;
  background: #fff;
  color: var(--inv-ink);
  font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 12px;
  line-height: 1.45;
  width: 100%;
  box-sizing: border-box;
}
.inv *, .inv *::before, .inv *::after { box-sizing: border-box; }
.inv p, .inv h1, .inv h2, .inv h3, .inv dl, .inv dd, .inv dt { margin: 0; padding: 0; }
.inv img { display: block; max-width: 100%; }
.inv table { width: 100%; border-collapse: collapse; border-spacing: 0; }

.inv-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.inv-brand { display: flex; align-items: flex-start; gap: 10px; min-width: 0; }
.inv-logo { width: 48px; height: 48px; object-fit: contain; flex: none; }
.inv-store { font-size: 16px; font-weight: 700; letter-spacing: -0.01em; line-height: 1.2; }
.inv-branch { margin-top: 1px; font-size: 10px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--inv-muted); }
.inv-contact { font-size: 11px; color: var(--inv-muted); }
.inv-titles { flex: none; text-align: right; }
.inv-doc-title { font-size: 18px; font-weight: 800; letter-spacing: 0.1em; text-transform: uppercase; line-height: 1.1; }
.inv-doc-number { margin-top: 2px; font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 12px; font-weight: 600; }
.inv-doc-state { margin-top: 2px; font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #b91c1c; }

.inv-meta { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 3px 24px; margin: 12px 0; }
.inv-meta-row { display: flex; justify-content: space-between; gap: 12px; }
.inv-label { color: var(--inv-muted); }
.inv-value { text-align: right; font-weight: 500; }

.inv-items { margin-top: 6px; }
.inv-items th, .inv-items td { padding: 5px 6px; text-align: left; vertical-align: top; }
.inv-items thead th { border-top: 2px solid var(--inv-ink); border-bottom: 1px solid var(--inv-ink); font-size: 10px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }
.inv-items tbody td { border-bottom: 1px solid var(--inv-line); }
.inv-items tbody tr:last-child td { border-bottom: none; }
.inv-item-name { font-weight: 600; }
.inv-item-sku { font-size: 10px; color: var(--inv-muted); }
.inv-num { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
.inv-col-no { width: 1.6em; color: var(--inv-muted); }

.inv-totals { margin: 12px 0 0 auto; width: 60%; }
.inv-line { display: flex; justify-content: space-between; gap: 16px; padding: 2px 0; }
.inv-line-strong { margin-top: 4px; padding-top: 6px; border-top: 2px solid var(--inv-ink); font-size: 15px; font-weight: 700; }

.inv-payments { margin-top: 14px; }
.inv-section-title { margin-bottom: 4px; font-size: 10px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--inv-muted); }

.inv-note { margin-top: 14px; padding: 6px 9px; border: 1px solid var(--inv-line); border-radius: 4px; font-size: 11px; }
.inv-foot { margin-top: 18px; text-align: center; color: var(--inv-muted); }
.inv-thanks { font-weight: 700; color: var(--inv-ink); }
.inv-fine { margin-top: 2px; font-size: 10px; }

@media screen {
  .inv { margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 4px; box-shadow: 0 10px 30px -12px rgba(15, 23, 42, 0.25); }
}
@media print {
  .inv { margin: 0; padding: 0; border: 0; border-radius: 0; box-shadow: none; }
}

body.inv-doc { margin: 0; padding: 0; background: #fff; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
`;

const THERMAL = `
.inv-thermal { max-width: 72mm; font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 11px; }
.inv-thermal .inv-head { flex-direction: column; align-items: center; gap: 4px; text-align: center; }
.inv-thermal .inv-brand { flex-direction: column; align-items: center; gap: 4px; }
.inv-thermal .inv-store { font-size: 14px; }
.inv-thermal .inv-titles { text-align: center; }
.inv-thermal .inv-doc-title { font-size: 12px; letter-spacing: 0.16em; }
.inv-thermal .inv-doc-number { font-size: 11px; }
.inv-thermal .inv-meta { grid-template-columns: 1fr; gap: 0; margin: 8px 0; }
.inv-thermal .inv-col-no, .inv-thermal .inv-disc-col { display: none; }
.inv-thermal .inv-items th, .inv-thermal .inv-items td { padding: 2px; }
.inv-thermal .inv-items thead th { border-top-width: 1px; }
.inv-thermal .inv-totals { width: 100%; }
.inv-thermal .inv-line-strong { font-size: 13px; }
.inv-thermal .inv-note { font-size: 10px; }
.inv-thermal .inv-foot { margin-top: 12px; }
@media screen { .inv-thermal { padding: 16px; } }
`;

const A4 = `
.inv-a4 { max-width: 180mm; font-size: 12px; }
.inv-a4 .inv-head { padding-bottom: 12px; border-bottom: 2px solid var(--inv-ink); }
.inv-a4 .inv-logo { width: 60px; height: 60px; }
.inv-a4 .inv-store { font-size: 20px; }
.inv-a4 .inv-doc-title { font-size: 24px; }
.inv-a4 .inv-meta { margin: 14px 0; }
.inv-a4 .inv-items { margin-top: 8px; }
.inv-a4 .inv-totals { width: 52%; }
`;

const PAGE: Record<InvoiceVariant, string> = {
  thermal: "@page { size: 80mm auto; margin: 3mm; }",
  a4: "@page { size: A4; margin: 12mm; }",
};

/** Build the invoice stylesheet for one layout. */
export function invoiceCss(variant: InvoiceVariant, options: { print?: boolean } = {}): string {
  const { print = true } = options;
  const parts = [BASE, variant === "a4" ? A4 : THERMAL];
  if (print) parts.push(PAGE[variant]);
  return parts.join("\n");
}
