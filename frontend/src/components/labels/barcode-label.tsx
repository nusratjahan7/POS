import { Barcode } from "@/components/barcode/barcode";
import type { LabelData } from "@/lib/labels/types";

/**
 * One printable label: product name, price, a scannable barcode and its code.
 *
 * Styled by the label stylesheet (`.lbl*`), not Tailwind — the same markup is
 * serialized into the print document.
 */
export function BarcodeLabel({ label }: { label: LabelData }) {
  return (
    <div className="lbl">
      <div className="lbl-name">{label.name}</div>
      {label.price ? <div className="lbl-price">{label.price}</div> : null}
      <Barcode value={label.code} showText={false} height={34} className="lbl-bc" />
      <div className="lbl-code">{label.code}</div>
      <div className="lbl-sku">{label.sku}</div>
    </div>
  );
}
