/**
 * A minimal Code 128 (subset B) encoder.
 *
 * The receipt prints offline and its markup is serialized into a detached print
 * document, so an image or a network barcode service is not an option. This
 * emits bar geometry in module units, which the caller draws as inline SVG —
 * real vector output that stays crisp on thermal paper and in a PDF.
 */

// The six element widths (bar, space, bar, space, bar, space) of each of the 107
// Code 128 symbols, indexed by symbol value. Index 106 is the stop pattern, whose
// trailing 2-module bar is the termination bar.
const PATTERNS = [
  "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312", "132212", "221213",
  "221312", "231212", "112232", "122132", "122231", "113222", "123122", "123221", "223211", "221132",
  "221231", "213212", "223112", "312131", "311222", "321122", "321221", "312212", "322112", "322211",
  "212123", "212321", "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
  "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121", "313121", "211331",
  "231131", "213113", "213311", "213131", "311123", "311321", "331121", "312113", "312311", "332111",
  "314111", "221411", "431111", "111224", "111422", "121124", "121421", "141122", "141221", "112214",
  "112412", "122114", "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
  "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112", "421211", "212141",
  "214121", "412121", "111143", "111341", "131141", "114113", "114311", "411113", "411311", "113141",
  "114131", "311141", "411131", "211412", "211214", "211232", "2331112",
];

const START_B = 104;
const STOP = 106;

/** A bar's left edge and width, both measured in modules. */
export type BarcodeBar = { x: number; width: number };

/** Encode `value` as Code 128B and return its bars plus the total module count. */
export function code128Bars(value: string): { bars: BarcodeBar[]; moduleCount: number } {
  const symbols = [...value].map((char) => {
    const code = char.charCodeAt(0);
    if (code < 32 || code > 126) {
      throw new Error(`Code 128B cannot encode ${JSON.stringify(char)}.`);
    }
    return code - 32;
  });

  // Every symbol is folded into the checksum with a position-weighted multiplier.
  const checksum =
    (START_B + symbols.reduce((sum, symbol, index) => sum + symbol * (index + 1), 0)) % 103;

  const bars: BarcodeBar[] = [];
  let x = 0;
  for (const symbol of [START_B, ...symbols, checksum, STOP]) {
    const widths = PATTERNS[symbol];
    for (let i = 0; i < widths.length; i += 1) {
      const width = Number(widths[i]);
      if (i % 2 === 0) bars.push({ x, width });
      x += width;
    }
  }

  return { bars, moduleCount: x };
}
