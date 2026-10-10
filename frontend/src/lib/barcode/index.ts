/**
 * Barcode generation facade.
 *
 * Picks the symbology from the value — a valid 13-digit number renders as EAN-13,
 * a 12-digit number as UPC-A, anything else as Code 128B — and always returns bar
 * geometry. `encodeBarcode` degrades gracefully: if a value looks like an EAN/UPC
 * but fails its check digit, it falls back to Code 128 rather than failing, so a
 * label or receipt never renders blank.
 */

import { encodeCode128 } from "@/lib/barcode/code128";
import { encodeEan13, encodeUpcA, isValidEan13 } from "@/lib/barcode/ean";
import type { BarcodeFormat, EncodedBarcode } from "@/lib/barcode/types";

export type { BarcodeBar, BarcodeFormat, EncodedBarcode } from "@/lib/barcode/types";
export { code128Bars } from "@/lib/barcode/code128";
export { EAN13_MODULE_COUNT, ean13CheckDigit, isValidEan13 } from "@/lib/barcode/ean";

/** Best symbology for a raw value: EAN-13, then UPC-A, otherwise Code 128. */
export function detectFormat(value: string): BarcodeFormat {
  const trimmed = value.trim();
  if (isValidEan13(trimmed)) return "ean13";
  if (/^\d{12}$/.test(trimmed)) return "upca";
  return "code128";
}

function encodeWith(format: BarcodeFormat, value: string): EncodedBarcode {
  if (format === "ean13") return encodeEan13(value);
  if (format === "upca") return encodeUpcA(value);
  return encodeCode128(value);
}

/**
 * Encode `value` with `format` (or the auto-detected one).
 *
 * Throws only when the value cannot be a Code 128 barcode at all (empty, or a
 * character outside printable ASCII). An EAN/UPC that fails validation silently
 * falls back to Code 128.
 */
export function encodeBarcode(value: string, format?: BarcodeFormat): EncodedBarcode {
  const trimmed = value.trim();
  if (!trimmed) throw new Error("A barcode value is required.");

  const chosen = format ?? detectFormat(trimmed);
  if (chosen === "code128") return encodeCode128(trimmed);

  try {
    return encodeWith(chosen, trimmed);
  } catch {
    // Bad check digit or wrong length for the requested retail format.
    return encodeCode128(trimmed);
  }
}
