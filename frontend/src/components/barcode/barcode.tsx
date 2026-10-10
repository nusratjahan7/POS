"use client";

import * as React from "react";

import { encodeBarcode, type BarcodeFormat, type EncodedBarcode } from "@/lib/barcode";
import { cn } from "@/lib/utils";

const DEFAULT_HEIGHT = 40;
/** How much shorter the data bars are than the guard bars (EAN/UPC). */
const GUARD_TRIM = 6;

export type BarcodeProps = {
  value: string;
  /** Force a symbology; otherwise it is detected from the value. */
  format?: BarcodeFormat;
  /** Print the human-readable characters under the bars. */
  showText?: boolean;
  height?: number;
  className?: string;
  /** Accessible name; defaults to "Barcode <text>". */
  ariaLabel?: string;
};

/**
 * Renders a barcode as inline SVG.
 *
 * Inline (never an image or a network service) so it survives being serialized
 * into a detached print document. A value that cannot be encoded renders a small
 * muted notice instead of throwing, so a bad code never breaks a list or a printout.
 */
export function Barcode({
  value,
  format,
  showText = true,
  height = DEFAULT_HEIGHT,
  className,
  ariaLabel,
}: BarcodeProps) {
  const encoded = React.useMemo<EncodedBarcode | null>(() => {
    try {
      return encodeBarcode(value, format);
    } catch {
      return null;
    }
  }, [value, format]);

  if (!encoded) {
    return (
      <span className={cn("text-muted-foreground text-xs", className)}>Unsupported barcode</span>
    );
  }

  // Code 128 has no guard pattern — every bar is full height.
  const fullHeight = encoded.format === "code128";

  const svg = (
    <svg
      className={className}
      viewBox={`0 0 ${encoded.moduleCount} ${height}`}
      width="100%"
      height={height}
      preserveAspectRatio="none"
      role="img"
      aria-label={ariaLabel ?? `Barcode ${encoded.text}`}
    >
      {encoded.bars.map((bar) => (
        <rect
          key={`${bar.x}-${bar.width}`}
          x={bar.x}
          y={0}
          width={bar.width}
          height={fullHeight || bar.guard ? height : height - GUARD_TRIM}
        />
      ))}
    </svg>
  );

  if (!showText) return svg;

  return (
    <span className="inline-flex flex-col items-center">
      {svg}
      <span className="mt-0.5 font-mono text-[0.625rem] leading-none tracking-[0.2em]">
        {encoded.text}
      </span>
    </span>
  );
}
