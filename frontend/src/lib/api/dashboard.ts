import { apiRequest } from "@/lib/api/client";
import { withQuery } from "@/lib/api/rbac";
import type {
  CategorySalesRow,
  PaymentMethodSalesRow,
  ProductSalesRow,
  ReportPreset,
  ReportRange,
  StockStatusRow,
} from "@/lib/api/reports";

export type DashboardParams = {
  preset?: ReportPreset;
  /** ISO `YYYY-MM-DD`; required when `preset` is `custom`. */
  date_from?: string;
  date_to?: string;
  branch_id?: string;
};

/** Today's trade, independent of the selected period. */
export type DashboardToday = {
  sales: string;
  orders: number;
  gross_profit: string;
  net_profit: string;
};

/** As-of-now figures that do not vary with the date window. */
export type DashboardStanding = {
  customers: number;
  products: number;
  low_stock: number;
  outstanding_due: string;
  supplier_due: string;
};

export type TrendPoint = {
  day: string;
  orders: number;
  revenue: string;
  profit: string;
};

export type RecentSaleRow = {
  id: string;
  sale_number: string;
  customer_name: string | null;
  total: string;
  status: string;
  sold_at: string;
};

export type RecentPaymentRow = {
  id: string;
  sale_number: string;
  method_name: string;
  amount: string;
  paid_at: string;
};

export type DashboardSnapshot = {
  as_of: string;
  range: ReportRange;
  today: DashboardToday;
  standing: DashboardStanding;
  trends: TrendPoint[];
  category_performance: CategorySalesRow[];
  payment_methods: PaymentMethodSalesRow[];
  top_products: ProductSalesRow[];
  recent_sales: RecentSaleRow[];
  low_stock: StockStatusRow[];
  recent_payments: RecentPaymentRow[];
};

export const dashboardApi = {
  snapshot(params: DashboardParams = {}): Promise<DashboardSnapshot> {
    return apiRequest<DashboardSnapshot>(withQuery("/dashboard", params));
  },
};
