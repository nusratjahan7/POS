/**
 * EAN-13 and UPC-A encoders.
 *
 * EAN-13 is the retail standard (13 digits, the last a check digit). UPC-A is the
 * North-American 12-digit form and is encoded here as EAN-13 with a leading zero —
 * the bars are identical, only the human-readable digits differ.
 *
 * Geometry: left guard (3) + 6 digits × 7 (42) + centre guard (5) + 6 digits × 7
 * (42) + right guard (3) = 95 modules. The three guards render taller.
 */

import type { BarcodeBar, EncodedBarcode } from "@/lib/barcode/types";

// Each digit is 7 modules. Left (odd parity) and right encodings are fixed; the
// even-parity "G" set is used for the left half under the first digit's parity.
const L = [
  "0001101", "0011001", "0010011", "0111101", "0100011",
  "0110001", "0101111", "0111011", "0110111", "0001011",
];
const G = [
  "0100111", "0110011", "0011011", "0100001", "0011101",
  "0111001", "0000101", "0010001", "0001001", "0010111",
];
const R = [
  "1110010", "1100110", "1101100", "1000010", "1011100",
  "1001110", "1010000", "1000100", "1001000", "1110100",
];

// Which of L/G encodes digits 2-7, chosen by the value of digit 1.
const PARITY = [
  "LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG",
  "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL",
];

const LEFT_GUARD = "101";
const CENTRE_GUARD = "01010";
const RIGHT_GUARD = "101";
export const EAN13_MODULE_COUNT = 95;

/** The check digit (13th) for the first twelve digits of an EAN-13. */
export function ean13CheckDigit(first12: string): number {
  let sum = 0;
  for (let index = 0; index < 12; index += 1) {
    sum += Number(first12[index]) * (index % 2 === 0 ? 1 : 3);
  }
  return (10 - (sum % 10)) % 10;
}

/** True when `value` is 13 digits whose final digit is the correct check digit. */
export function isValidEan13(value: string): boolean {
  return /^\d{13}$/.test(value) && Number(value[12]) === ean13CheckDigit(value.slice(0, 12));
}

/** Push one bit pattern, emitting a bar for every `1`. Returns the new x. */
function pushPattern(bars: BarcodeBar[], x: number, pattern: string, guard: boolean): number {
  for (let i = 0; i < pattern.length; i += 1) {
    if (pattern[i] === "1") bars.push({ x: x + i, width: 1, guard });
  }
  return x + pattern.length;
}

/** Encode a validated 13-digit EAN-13 value. */
export function encodeEan13(value: string): EncodedBarcode {
  if (!/^\d{13}$/.test(value)) {
    throw new Error(`EAN-13 needs exactly 13 digits, got ${value.length}.`);
  }
  if (!isValidEan13(value)) {
    throw new Error("EAN-13 check digit does not match.");
  }

  const bars: BarcodeBar[] = [];
  let x = pushPattern(bars, 0, LEFT_GUARD, true);

  const parity = PARITY[Number(value[0])];
  for (let i = 1; i <= 6; i += 1) {
    const digit = Number(value[i]);
    x = pushPattern(bars, x, parity[i - 1] === "L" ? L[digit] : G[digit], false);
  }

  x = pushPattern(bars, x, CENTRE_GUARD, true);
  for (let i = 7; i <= 12; i += 1) {
    x = pushPattern(bars, x, R[Number(value[i])], false);
  }
  x = pushPattern(bars, x, RIGHT_GUARD, true);

  return { format: "ean13", bars, moduleCount: x, text: value };
}

/** Encode a 12-digit UPC-A value (as EAN-13 with a leading zero). */
export function encodeUpcA(value: string): EncodedBarcode {
  if (!/^\d{12}$/.test(value)) {
    throw new Error(`UPC-A needs exactly 12 digits, got ${value.length}.`);
  }
  const encoded = encodeEan13(`0${value}`);
  return { ...encoded, format: "upca", text: value };
}
