/**
 * The barcode label stylesheet.
 *
 * Self-contained (no Tailwind, no app tokens) because it is used in two places:
 * the on-screen preview and a detached print document. `print: false` omits the
 * `@page` rules so an injected `<style>` in the live app cannot change the paper
 * size of anything else.
 *
 * Two physical targets:
 * - `thermal` — a 50 × 25 mm label roll; one label per page.
 * - `a4` — A4 sheets of 63.5 × 38.1 mm labels in a 3 × 8 grid (24 per page).
 */

import type { LabelLayout } from "@/lib/labels/types";

export type { LabelData, LabelLayout } from "@/lib/labels/types";

export const THERMAL_LABEL = { widthMm: 50, heightMm: 25 } as const;
export const A4_LABEL = { widthMm: 63.5, heightMm: 38.1, columns: 3, rows: 8, perPage: 24 } as const;

const BASE = `
.lbl-doc { margin: 0; padding: 0; background: #fff; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.lbl-sheet { box-sizing: border-box; }
.lbl {
  box-sizing: border-box;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 0.8mm; padding: 2mm; overflow: hidden;
  background: #fff; color: #0f172a;
  font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
.lbl-name { max-width: 100%; font-size: 8pt; font-weight: 700; line-height: 1.15; text-align: center; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.lbl-price { font-size: 12pt; font-weight: 800; letter-spacing: -0.01em; }
.lbl-bc { display: block; width: 100%; }
.lbl-code { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 7pt; letter-spacing: 0.12em; }
.lbl-sku { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 6pt; color: #64748b; }
`;

const THERMAL = `
.lbl-sheet[data-layout="thermal"] .lbl { width: 50mm; height: 25mm; break-after: page; }
.lbl-sheet[data-layout="thermal"] .lbl:last-child { break-after: auto; }
.lbl-sheet[data-layout="thermal"] .lbl-name { font-size: 7.5pt; -webkit-line-clamp: 1; }
.lbl-sheet[data-layout="thermal"] .lbl-price { font-size: 11pt; }
`;

const A4 = `
.lbl-sheet[data-layout="a4"] { display: grid; grid-template-columns: repeat(3, 63.5mm); grid-auto-rows: 38.1mm; }
.lbl-sheet[data-layout="a4"] .lbl { break-inside: avoid; }
`;

const PAGE: Record<LabelLayout, string> = {
  thermal: "@page { size: 50mm 25mm; margin: 0; }",
  a4: "@page { size: A4; margin: 0; }",
};

const SCREEN = `
@media screen {
  .lbl-doc { padding: 12px; background: #f1f5f9; }
  .lbl { outline: 0.5px dashed #cbd5e1; }
  .lbl-sheet[data-layout="a4"] { margin: 0 auto; background: #fff; box-shadow: 0 10px 30px -12px rgba(15, 23, 42, 0.3); }
  .lbl-sheet[data-layout="thermal"] { display: flex; flex-direction: column; align-items: center; gap: 8px; }
}
`;

/** Build the label stylesheet for one layout. */
export function labelCss(layout: LabelLayout, options: { print?: boolean } = {}): string {
  const { print = true } = options;
  const parts = [BASE, layout === "a4" ? A4 : THERMAL];
  if (print) parts.push(PAGE[layout]);
  parts.push(SCREEN);
  return parts.join("\n");
}
