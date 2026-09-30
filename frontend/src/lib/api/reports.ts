import { apiDownload, apiRequest, type DownloadedFile } from "@/lib/api/client";
import { withQuery } from "@/lib/api/rbac";

export type ReportPreset =
  | "today"
  | "yesterday"
  | "this_week"
  | "this_month"
  | "this_year"
  | "custom";

export type ReportName = "sales" | "purchases" | "inventory" | "financial";

/** CSV and Excel download; HTML is what the browser prints to PDF. */
export type ExportFormat = "csv" | "xlsx" | "html";

export type ReportParams = {
  preset?: ReportPreset;
  /** ISO `YYYY-MM-DD`; required when `preset` is `custom`. */
  date_from?: string;
  date_to?: string;
  branch_id?: string;
};

export type ReportRange = {
  start: string;
  end: string;
  preset: string;
};

// --- Sales -----------------------------------------------------------------
export type SalesSummary = {
  total_sales: string;
  order_count: number;
  average_order_value: string;
  items_sold: string;
  discount: string;
  tax: string;
  refunded_amount: string;
  returns_count: number;
};

export type SalesDailyPoint = {
  day: string;
  total: string;
  orders: number;
};

export type ProductSalesRow = {
  product_id: string | null;
  name: string;
  sku: string;
  quantity: string;
  net: string;
  cost: string;
  profit: string;
};

export type CategorySalesRow = {
  category_id: string | null;
  name: string;
  quantity: string;
  net: string;
};

export type CashierSalesRow = {
  cashier_id: string | null;
  name: string;
  order_count: number;
  total: string;
};

export type BranchSalesRow = {
  branch_id: string | null;
  name: string;
  order_count: number;
  total: string;
};

export type PaymentMethodSalesRow = {
  payment_method_id: string | null;
  name: string;
  kind: string;
  count: number;
  amount: string;
};

export type SalesReport = {
  range: ReportRange;
  summary: SalesSummary;
  daily: SalesDailyPoint[];
  by_product: ProductSalesRow[];
  by_category: CategorySalesRow[];
  by_cashier: CashierSalesRow[];
  by_branch: BranchSalesRow[];
  by_payment_method: PaymentMethodSalesRow[];
};

// --- Purchases -------------------------------------------------------------
export type PurchaseSummary = {
  total_purchases: string;
  purchase_count: number;
  paid: string;
  outstanding_due: string;
};

export type SupplierPurchaseRow = {
  supplier_id: string | null;
  name: string;
  count: number;
  total: string;
  due: string;
};

export type PurchaseReport = {
  range: ReportRange;
  summary: PurchaseSummary;
  by_supplier: SupplierPurchaseRow[];
};

// --- Inventory -------------------------------------------------------------
export type InventoryTotals = {
  product_count: number;
  stock_value_cost: string;
  stock_value_retail: string;
  total_quantity: string;
  in_stock: number;
  low_stock: number;
  out_of_stock: number;
};

export type StockStatusRow = {
  product_id: string;
  name: string;
  sku: string;
  unit: string;
  quantity: string;
  minimum_stock: string;
  stock_status: string;
};

export type MovementTypeRow = {
  movement_type: string;
  count: number;
  net_quantity: string;
};

export type AdjustmentSummary = {
  count: number;
  net_quantity: string;
  damage_count: number;
  damage_quantity: string;
};

export type InventoryReport = {
  as_of: string;
  /** Movements and adjustments cover this window; stock value is as-of-now. */
  range: ReportRange;
  totals: InventoryTotals;
  low_stock: StockStatusRow[];
  out_of_stock: StockStatusRow[];
  movements: MovementTypeRow[];
  adjustments: AdjustmentSummary;
};

// --- Financial -------------------------------------------------------------
export type FinancialReport = {
  range: ReportRange;
  revenue: string;
  cost: string;
  gross_profit: string;
  gross_margin: string;
  expenses: string;
  net_profit: string;
  customer_due: string;
  supplier_due: string;
};

export const reportsApi = {
  sales(params: ReportParams = {}): Promise<SalesReport> {
    return apiRequest<SalesReport>(withQuery("/reports/sales", params));
  },

  purchases(params: ReportParams = {}): Promise<PurchaseReport> {
    return apiRequest<PurchaseReport>(withQuery("/reports/purchases", params));
  },

  inventory(params: ReportParams = {}): Promise<InventoryReport> {
    return apiRequest<InventoryReport>(withQuery("/reports/inventory", params));
  },

  financial(params: ReportParams = {}): Promise<FinancialReport> {
    return apiRequest<FinancialReport>(withQuery("/reports/financial", params));
  },

  /** Fetch a report as a file. Authenticated, so it goes through the API client. */
  export(report: ReportName, format: ExportFormat, params: ReportParams = {}): Promise<DownloadedFile> {
    return apiDownload(withQuery(`/reports/${report}/export`, { format, ...params }));
  },
};
