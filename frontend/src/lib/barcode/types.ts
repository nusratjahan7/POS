/** Symbologies the frontend can generate. */
export type BarcodeFormat = "ean13" | "upca" | "code128";

/** A bar's left edge and width, in module units. `guard` bars render taller. */
export type BarcodeBar = { x: number; width: number; guard?: boolean };

export type EncodedBarcode = {
  format: BarcodeFormat;
  bars: BarcodeBar[];
  /** Total width in modules — the SVG viewBox width. */
  moduleCount: number;
  /** Human-readable characters printed under the bars. */
  text: string;
};
