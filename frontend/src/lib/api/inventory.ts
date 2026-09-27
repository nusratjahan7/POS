import { apiRequest } from "@/lib/api/client";
import type { BranchOption } from "@/lib/api/rbac";
import { withQuery, type Page } from "@/lib/api/rbac";

export type StockStatus = "in_stock" | "low_stock" | "out_of_stock";

export type MovementType = "opening" | "stock_in" | "stock_out" | "adjustment" | "damage";

export type StockProduct = {
  id: string;
  name: string;
  sku: string;
  unit: string;
  minimum_stock: string;
  image_url: string | null;
};

export type StockLevel = {
  id: string;
  product: StockProduct;
  branch: BranchOption;
  quantity: string;
  stock_status: StockStatus;
  is_low_stock: boolean;
  updated_at: string;
};

export type Movement = {
  id: string;
  product: StockProduct;
  branch: BranchOption;
  quantity: string;
  movement_type: MovementType;
  reference_type: string;
  reference_id: string | null;
  previous_stock: string;
  new_stock: string;
  note: string | null;
  user: { id: string; full_name: string; email: string } | null;
  created_at: string;
};

export type InventorySummary = {
  total_levels: number;
  in_stock: number;
  low_stock: number;
  out_of_stock: number;
  total_quantity: string;
};

export type MovementPayload = {
  product_id: string;
  branch_id: string;
  movement_type: MovementType;
  /** Signed change: positive increases stock, negative decreases it. */
  quantity: string;
  reference_type?: "manual" | "opening" | "purchase" | "sale";
  reference_id?: string | null;
  note?: string | null;
};

export type StockListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  branch_id?: string;
  category_id?: string;
  status?: StockStatus;
  sort?: string;
};

export type MovementListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  product_id?: string;
  branch_id?: string;
  movement_type?: MovementType;
  sort?: string;
};

export const inventoryApi = {
  listStock(params: StockListParams = {}): Promise<Page<StockLevel>> {
    return apiRequest<Page<StockLevel>>(withQuery("/inventory/stock", { page_size: 20, ...params }));
  },

  summary(branchId?: string): Promise<InventorySummary> {
    return apiRequest<InventorySummary>(withQuery("/inventory/stock/summary", { branch_id: branchId }));
  },

  listMovements(params: MovementListParams = {}): Promise<Page<Movement>> {
    return apiRequest<Page<Movement>>(
      withQuery("/inventory/movements", { page_size: 20, ...params }),
    );
  },

  createMovement(payload: MovementPayload): Promise<Movement> {
    return apiRequest<Movement>("/inventory/movements", { method: "POST", body: payload });
  },
};
