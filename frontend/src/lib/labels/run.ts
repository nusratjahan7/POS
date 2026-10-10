import type { LabelData } from "@/lib/labels/types";

/**
 * Expand a set of labels into a print run: each label repeated `copies` times.
 *
 * Pure so the label count and ordering can be asserted without a DOM. `copies`
 * is clamped to at least one.
 */
export function buildLabelRun(seeds: readonly LabelData[], copies: number): LabelData[] {
  const repeat = Math.max(1, Math.floor(copies) || 1);
  const run: LabelData[] = [];
  for (const seed of seeds) {
    for (let copy = 0; copy < repeat; copy += 1) run.push(seed);
  }
  return run;
}
