import { BarcodeLabel } from "@/components/labels/barcode-label";
import type { LabelData, LabelLayout } from "@/lib/labels/types";

/**
 * A sheet of labels in one physical layout. The container carries `data-layout`
 * so the layouts share one stylesheet with a `[data-layout="…"]` selector.
 */
export function LabelSheet({
  labels,
  layout,
}: {
  labels: readonly LabelData[];
  layout: LabelLayout;
}) {
  return (
    <div className="lbl-sheet" data-layout={layout}>
      {labels.map((label, index) => (
        <BarcodeLabel key={`${label.code}-${index}`} label={label} />
      ))}
    </div>
  );
}
