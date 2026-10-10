/** Physical label layouts the printer supports. */
export type LabelLayout = "thermal" | "a4";

/** One label's worth of data. */
export type LabelData = {
  name: string;
  /** The scannable code: the product's barcode, or its SKU when it has none. */
  code: string;
  sku: string;
  /** Pre-formatted price, or null when the label omits it. */
  price: string | null;
};
