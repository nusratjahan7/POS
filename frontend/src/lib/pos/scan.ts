import type { PosProduct } from "@/lib/api/pos";

/**
 * The product a scanned or typed code refers to, matched **exactly** on barcode or
 * SKU (case-insensitive).
 *
 * A barcode scanner behaves like a keyboard: it types the whole code quickly and
 * presses Enter. Matching exactly — never a substring — is what keeps a scan from
 * landing on the wrong product, and lets the caller fall back to a server lookup
 * when nothing in the loaded page matches.
 */
export function findExactMatch(
  products: readonly PosProduct[],
  term: string,
): PosProduct | undefined {
  const lowered = term.trim().toLowerCase();
  if (!lowered) return undefined;

  return products.find(
    (product) =>
      product.sku.toLowerCase() === lowered ||
      (product.barcode !== null && product.barcode.toLowerCase() === lowered),
  );
}
