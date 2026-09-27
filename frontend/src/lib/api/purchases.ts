import { apiRequest } from "@/lib/api/client";
import { withQuery, type Page } from "@/lib/api/rbac";
import type { SupplierOption } from "@/lib/api/suppliers";

export type PurchaseStatus = "draft" | "pending" | "received" | "cancelled";

/** Only draft/pending can be set by the client; the rest are server transitions. */
export type EditablePurchaseStatus = "draft" | "pending";

export type PurchaseItemInput = {
  product_id: string;
  quantity: string;
  unit_price: string;
};

export type PurchaseItem = {
  id: string;
  product: { id: string; name: string; sku: string; unit: string };
  quantity: string;
  unit_price: string;
  subtotal: string;
};

type BranchRef = { id: string; name: string; code: string };

export type PurchaseSummary = {
  id: string;
  purchase_number: string;
  supplier: SupplierOption;
  branch: BranchRef;
  purchase_date: string;
  subtotal: string;
  discount: string;
  tax: string;
  total: string;
  paid: string;
  due: string;
  status: PurchaseStatus;
  created_at: string;
};

export type Purchase = PurchaseSummary & {
  note: string | null;
  created_by: { id: string; full_name: string } | null;
  items: PurchaseItem[];
  received_at: string | null;
  cancelled_at: string | null;
  updated_at: string;
};

export type PurchasePayload = {
  supplier_id: string;
  branch_id: string;
  purchase_date: string;
  discount?: string;
  tax?: string;
  paid?: string;
  status?: EditablePurchaseStatus;
  note?: string | null;
  items: PurchaseItemInput[];
};

export type PurchaseListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  supplier_id?: string;
  branch_id?: string;
  status?: PurchaseStatus;
  date_from?: string;
  date_to?: string;
  sort?: string;
};

export const purchasesApi = {
  list(params: PurchaseListParams = {}): Promise<Page<PurchaseSummary>> {
    return apiRequest<Page<PurchaseSummary>>(withQuery("/purchases", { page_size: 20, ...params }));
  },

  get(purchaseId: string): Promise<Purchase> {
    return apiRequest<Purchase>(`/purchases/${purchaseId}`);
  },

  create(payload: PurchasePayload): Promise<Purchase> {
    return apiRequest<Purchase>("/purchases", { method: "POST", body: payload });
  },

  update(purchaseId: string, payload: Partial<PurchasePayload>): Promise<Purchase> {
    return apiRequest<Purchase>(`/purchases/${purchaseId}`, { method: "PATCH", body: payload });
  },

  /** Receive a purchase — the only call that moves stock. */
  receive(purchaseId: string): Promise<Purchase> {
    return apiRequest<Purchase>(`/purchases/${purchaseId}/receive`, { method: "POST" });
  },

  cancel(purchaseId: string): Promise<Purchase> {
    return apiRequest<Purchase>(`/purchases/${purchaseId}/cancel`, { method: "POST" });
  },

  remove(purchaseId: string): Promise<void> {
    return apiRequest<void>(`/purchases/${purchaseId}`, { method: "DELETE" });
  },
};
