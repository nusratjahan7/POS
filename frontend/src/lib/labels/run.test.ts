import { describe, expect, it } from "vitest";

import { buildLabelRun } from "./run";
import type { LabelData } from "./types";

const seed: LabelData = { name: "Beans", code: "BEAN-1", sku: "BEAN-1", price: "$2.00" };

describe("buildLabelRun", () => {
  it("repeats every label by the copy count, keeping order", () => {
    const run = buildLabelRun([seed, { ...seed, code: "X" }], 2);

    expect(run).toHaveLength(4);
    expect(run.map((label) => label.code)).toEqual(["BEAN-1", "BEAN-1", "X", "X"]);
  });

  it("clamps copies to at least one", () => {
    expect(buildLabelRun([seed], 0)).toHaveLength(1);
    expect(buildLabelRun([seed], -3)).toHaveLength(1);
  });

  it("returns nothing for an empty selection", () => {
    expect(buildLabelRun([], 5)).toEqual([]);
  });
});
