import { describe, expect, it } from "vitest";

import type { TransferStatus } from "@/lib/api/transfers";
import { TRANSFER_FLOW, TRANSFER_STATUS_META, availableActions } from "./status";

const ALL = { write: true, approve: true, ship: true, receive: true };
const NONE = { write: false, approve: false, ship: false, receive: false };

describe("transfer status metadata", () => {
  it("covers every status with a label and badge", () => {
    const statuses: TransferStatus[] = [
      "draft",
      "requested",
      "approved",
      "shipped",
      "received",
      "cancelled",
    ];
    for (const status of statuses) {
      expect(TRANSFER_STATUS_META[status].label).toBeTruthy();
      expect(TRANSFER_STATUS_META[status].variant).toBeTruthy();
    }
  });

  it("orders the workflow with received last", () => {
    expect(TRANSFER_FLOW[0]).toBe("draft");
    expect(TRANSFER_FLOW.at(-1)).toBe("received");
    expect(TRANSFER_FLOW).not.toContain("cancelled");
  });
});

describe("availableActions", () => {
  it("shows the next workflow step plus cancel before shipping", () => {
    expect(availableActions("draft", ALL)).toEqual(["request", "approve", "cancel"]);
    expect(availableActions("requested", ALL)).toEqual(["approve", "cancel"]);
    expect(availableActions("approved", ALL)).toEqual(["ship", "cancel"]);
    expect(availableActions("shipped", ALL)).toEqual(["receive"]);
    expect(availableActions("received", ALL)).toEqual([]);
  });

  it("never offers an action the caller cannot perform", () => {
    expect(availableActions("draft", NONE)).toEqual([]);
    expect(availableActions("shipped", { ...NONE, receive: true })).toEqual(["receive"]);
    expect(availableActions("approved", { ...NONE, ship: true })).toEqual(["ship"]);
  });

  it("offers nothing once a transfer is cancelled", () => {
    expect(availableActions("cancelled", ALL)).toEqual([]);
  });
});
