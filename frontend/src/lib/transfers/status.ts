import type { TransferStatus } from "@/lib/api/transfers";

export type BadgeVariant =
  | "default"
  | "neutral"
  | "outline"
  | "success"
  | "warning"
  | "destructive"
  | "info";

type StatusMeta = {
  label: string;
  variant: BadgeVariant;
  /** Short line shown under the status in listings and the detail header. */
  description: string;
};

/** The order the transfer moves through; cancelled is a side exit. */
export const TRANSFER_FLOW: TransferStatus[] = [
  "draft",
  "requested",
  "approved",
  "shipped",
  "received",
];

export const TRANSFER_STATUS_META: Record<TransferStatus, StatusMeta> = {
  draft: { label: "Draft", variant: "outline", description: "Not yet submitted." },
  requested: {
    label: "Requested",
    variant: "info",
    description: "Waiting for approval.",
  },
  approved: {
    label: "Approved",
    variant: "info",
    description: "Cleared to ship from the source branch.",
  },
  shipped: {
    label: "Shipped",
    variant: "warning",
    description: "In transit — source stock deducted, awaiting receipt.",
  },
  received: {
    label: "Received",
    variant: "success",
    description: "Complete — destination stock increased.",
  },
  cancelled: {
    label: "Cancelled",
    variant: "destructive",
    description: "Stopped before shipping. No stock moved.",
  },
};

export type TransferAction = "request" | "approve" | "ship" | "receive" | "cancel";

type Permissions = {
  write: boolean;
  approve: boolean;
  ship: boolean;
  receive: boolean;
};

/**
 * The actions the *workflow* allows for a status, filtered by what the caller
 * may do. The API re-checks both, so this only decides which buttons to show.
 */
export function availableActions(status: TransferStatus, can: Permissions): TransferAction[] {
  const actions: TransferAction[] = [];
  if (status === "draft" && can.write) actions.push("request");
  if ((status === "draft" || status === "requested") && can.approve) actions.push("approve");
  if (status === "approved" && can.ship) actions.push("ship");
  if (status === "shipped" && can.receive) actions.push("receive");
  if ((status === "draft" || status === "requested" || status === "approved") && can.write) {
    actions.push("cancel");
  }
  return actions;
}
