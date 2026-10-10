import { labelCss } from "@/lib/labels/styles";
import type { LabelLayout } from "@/lib/labels/types";
import { buildPrintDocument, printHtml } from "@/lib/printing/print-html";

/** Wrap rendered label markup in a standalone document with the label styles. */
export function buildLabelDocument(innerHtml: string, layout: LabelLayout): string {
  return buildPrintDocument(innerHtml, {
    title: "Barcode labels",
    css: labelCss(layout),
    bodyClass: "lbl-doc",
  });
}

/** Print a sheet of barcode labels through the browser. */
export function printLabels(innerHtml: string, layout: LabelLayout): void {
  printHtml(innerHtml, {
    title: "Barcode labels",
    css: labelCss(layout),
    bodyClass: "lbl-doc",
  });
}
