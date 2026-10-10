import { Barcode } from "@/components/barcode/barcode";

/**
 * The receipt's scannable barcode — the sale number. Inline SVG (the class lands
 * on the `svg` itself) so it survives being serialized into the print document.
 */
export function InvoiceBarcode({ value }: { value: string }) {
  return (
    <Barcode
      value={value}
      showText={false}
      height={40}
      className="inv-barcode"
      ariaLabel={`Barcode for ${value}`}
    />
  );
}
