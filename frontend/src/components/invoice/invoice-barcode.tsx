import { code128Bars } from "@/lib/invoice/barcode";

const HEIGHT = 40;

/**
 * The receipt's scannable barcode — the sale number, drawn as inline SVG so it
 * survives being serialized into the print document.
 */
export function InvoiceBarcode({ value }: { value: string }) {
  const { bars, moduleCount } = code128Bars(value);

  return (
    <svg
      className="inv-barcode"
      viewBox={`0 0 ${moduleCount} ${HEIGHT}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label={`Barcode for ${value}`}
    >
      {bars.map((bar) => (
        <rect key={bar.x} x={bar.x} y={0} width={bar.width} height={HEIGHT} />
      ))}
    </svg>
  );
}
