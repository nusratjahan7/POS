import { apiRequest } from "@/lib/api/client";
import { withQuery, type Page } from "@/lib/api/rbac";

export type ExpenseCategory = {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ExpenseCategoryOption = {
  id: string;
  name: string;
};

export type ExpensePaymentMethod = {
  id: string;
  name: string;
  code: string;
  kind: string;
  /** True for cash — the method that draws on a register's drawer. */
  opens_cash_drawer: boolean;
};

/** The drawer a cash expense was paid from. */
export type ExpenseRegisterSession = {
  id: string;
  status: string;
  register: { id: string; name: string };
};

export type Expense = {
  id: string;
  branch: { id: string; name: string; code: string };
  category: { id: string; name: string };
  payment_method: ExpensePaymentMethod;
  register_session: ExpenseRegisterSession | null;
  amount: string;
  description: string | null;
  reference: string | null;
  spent_at: string;
  created_by: { id: string; full_name: string } | null;
  created_at: string;
};

export type ExpensePayload = {
  branch_id: string;
  category_id: string;
  payment_method_id: string;
  amount: string;
  description?: string | null;
  reference?: string | null;
  /** ISO `YYYY-MM-DD`. */
  spent_at: string;
  /** Required when the method is cash — the open session it is paid from. */
  register_session_id?: string | null;
};

export type ExpenseListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  branch_id?: string;
  category_id?: string;
  payment_method_id?: string;
  /** ISO `YYYY-MM-DD`. */
  date_from?: string;
  date_to?: string;
  sort?: string;
};

export const expenseCategoriesApi = {
  list(
    params: { page?: number; page_size?: number; search?: string; is_active?: boolean } = {},
  ): Promise<Page<ExpenseCategory>> {
    return apiRequest<Page<ExpenseCategory>>(
      withQuery("/expense-categories", { page_size: 100, ...params }),
    );
  },

  options(): Promise<ExpenseCategoryOption[]> {
    return apiRequest<ExpenseCategoryOption[]>("/expense-categories/options");
  },

  create(payload: { name: string; description?: string | null; is_active?: boolean }) {
    return apiRequest<ExpenseCategory>("/expense-categories", { method: "POST", body: payload });
  },

  update(
    categoryId: string,
    payload: Partial<{ name: string; description: string | null; is_active: boolean }>,
  ) {
    return apiRequest<ExpenseCategory>(`/expense-categories/${categoryId}`, {
      method: "PATCH",
      body: payload,
    });
  },

  remove(categoryId: string): Promise<void> {
    return apiRequest<void>(`/expense-categories/${categoryId}`, { method: "DELETE" });
  },
};

export const expensesApi = {
  list(params: ExpenseListParams = {}): Promise<Page<Expense>> {
    return apiRequest<Page<Expense>>(withQuery("/expenses", { page_size: 20, ...params }));
  },

  /** Total spend for the current filters. */
  total(params: ExpenseListParams = {}): Promise<{ amount: string }> {
    return apiRequest<{ amount: string }>(withQuery("/expenses/summary", { ...params }));
  },

  create(payload: ExpensePayload): Promise<Expense> {
    return apiRequest<Expense>("/expenses", { method: "POST", body: payload });
  },

  remove(expenseId: string): Promise<void> {
    return apiRequest<void>(`/expenses/${expenseId}`, { method: "DELETE" });
  },
};
