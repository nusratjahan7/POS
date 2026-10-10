import { apiRequest } from "@/lib/api/client";
import { withQuery, type Page } from "@/lib/api/rbac";

export type TransferStatus =
  | "draft"
  | "requested"
  | "approved"
  | "shipped"
  | "received"
  | "cancelled";

export type TransferBranch = {
  id: string;
  name: string;
  code: string;
};

export type TransferUser = {
  id: string;
  full_name: string;
};

export type TransferLine = {
  id: string;
  product_id: string;
  product_name: string;
  sku: string;
  quantity: string;
};

export type Transfer = {
  id: string;
  transfer_number: string;
  status: TransferStatus;
  from_branch: TransferBranch;
  to_branch: TransferBranch;
  reference: string | null;
  note: string | null;
  cancel_reason: string | null;
  items: TransferLine[];
  item_count: number;
  total_quantity: string;
  created_by: TransferUser | null;
  requested_by: TransferUser | null;
  approved_by: TransferUser | null;
  shipped_by: TransferUser | null;
  received_by: TransferUser | null;
  cancelled_by: TransferUser | null;
  requested_at: string | null;
  approved_at: string | null;
  shipped_at: string | null;
  received_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
};

export type TransferSummary = Pick<
  Transfer,
  | "id"
  | "transfer_number"
  | "status"
  | "from_branch"
  | "to_branch"
  | "reference"
  | "items"
  | "item_count"
  | "total_quantity"
  | "created_at"
  | "shipped_at"
  | "received_at"
>;

export type TransferLineInput = {
  product_id: string;
  quantity: string;
};

export type TransferPayload = {
  from_branch_id: string;
  to_branch_id: string;
  reference?: string | null;
  note?: string | null;
  items: TransferLineInput[];
  /** Send straight to the approval queue instead of saving as a draft. */
  submit?: boolean;
};

export type TransferListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  status?: TransferStatus;
  branch_id?: string;
  from_branch_id?: string;
  to_branch_id?: string;
  date_from?: string;
  date_to?: string;
  sort?: string;
};

export const transfersApi = {
  list(params: TransferListParams = {}): Promise<Page<TransferSummary>> {
    return apiRequest<Page<TransferSummary>>(withQuery("/transfers", { page_size: 10, ...params }));
  },

  get(transferId: string): Promise<Transfer> {
    return apiRequest<Transfer>(`/transfers/${transferId}`);
  },

  create(payload: TransferPayload): Promise<Transfer> {
    return apiRequest<Transfer>("/transfers", { method: "POST", body: payload });
  },

  update(transferId: string, payload: Partial<TransferPayload>): Promise<Transfer> {
    return apiRequest<Transfer>(`/transfers/${transferId}`, { method: "PATCH", body: payload });
  },

  request(transferId: string): Promise<Transfer> {
    return apiRequest<Transfer>(`/transfers/${transferId}/request`, { method: "POST" });
  },

  approve(transferId: string): Promise<Transfer> {
    return apiRequest<Transfer>(`/transfers/${transferId}/approve`, { method: "POST" });
  },

  ship(transferId: string): Promise<Transfer> {
    return apiRequest<Transfer>(`/transfers/${transferId}/ship`, { method: "POST" });
  },

  receive(transferId: string): Promise<Transfer> {
    return apiRequest<Transfer>(`/transfers/${transferId}/receive`, { method: "POST" });
  },

  cancel(transferId: string, reason?: string): Promise<Transfer> {
    return apiRequest<Transfer>(`/transfers/${transferId}/cancel`, {
      method: "POST",
      body: { reason: reason ?? null },
    });
  },
};
