import { apiRequest } from "@/lib/api/client";
import { withQuery, type Page } from "@/lib/api/rbac";

export type SessionStatus = "open" | "closed";
export type CashMovementType = "sale" | "refund" | "expense" | "cash_in" | "cash_out";

export type RegisterSession = {
  id: string;
  /** The till this session belongs to. */
  register: { id: string; name: string };
  branch: { id: string; name: string; code: string };
  opening_cash: string;
  status: SessionStatus;
  opened_by: { id: string; full_name: string } | null;
  opened_at: string;
  closed_by: { id: string; full_name: string } | null;
  closed_at: string | null;
  /** Live while the session is open; the reconciled figure once closed. */
  expected_cash: string | null;
  actual_cash: string | null;
  /** actual − expected; negative is short. */
  difference: string | null;
  closing_note: string | null;
};

export type CashMovement = {
  id: string;
  movement_type: CashMovementType;
  /** Signed: positive into the drawer, negative out. */
  amount: string;
  reference_type: string;
  reference_id: string | null;
  note: string | null;
  user: { id: string; full_name: string } | null;
  created_at: string;
};

/** How a session's drawer adds up. */
export type SessionSummary = {
  opening_cash: string;
  cash_sales: string;
  cash_refunds: string;
  cash_expenses: string;
  cash_in: string;
  cash_out: string;
  expected_cash: string;
  movements: CashMovement[];
};

export type RegisterSessionDetail = {
  session: RegisterSession;
  summary: SessionSummary;
};

export type SessionListParams = {
  page?: number;
  page_size?: number;
  register_id?: string;
  branch_id?: string;
  status?: SessionStatus;
  cashier_id?: string;
  /** ISO `YYYY-MM-DD`. */
  date_from?: string;
  date_to?: string;
  sort?: string;
};

export const registerSessionsApi = {
  list(params: SessionListParams = {}): Promise<Page<RegisterSession>> {
    return apiRequest<Page<RegisterSession>>(
      withQuery("/register-sessions", { page_size: 20, ...params }),
    );
  },

  /** The open session for a register, or null. */
  current(registerId: string): Promise<RegisterSessionDetail | null> {
    return apiRequest<RegisterSessionDetail | null>(
      withQuery("/register-sessions/current", { register_id: registerId }),
    );
  },

  openSessions(branchId?: string): Promise<RegisterSession[]> {
    return apiRequest<RegisterSession[]>(
      withQuery("/register-sessions/open", { branch_id: branchId }),
    );
  },

  get(sessionId: string): Promise<RegisterSessionDetail> {
    return apiRequest<RegisterSessionDetail>(`/register-sessions/${sessionId}`);
  },

  /** Open a till with its float. */
  open(payload: { register_id: string; opening_cash?: string }): Promise<RegisterSessionDetail> {
    return apiRequest<RegisterSessionDetail>("/register-sessions", {
      method: "POST",
      body: payload,
    });
  },

  close(
    sessionId: string,
    payload: { actual_cash: string; note?: string | null },
  ): Promise<RegisterSessionDetail> {
    return apiRequest<RegisterSessionDetail>(`/register-sessions/${sessionId}/close`, {
      method: "POST",
      body: payload,
    });
  },

  cashIn(
    sessionId: string,
    payload: { amount: string; note?: string | null },
  ): Promise<RegisterSessionDetail> {
    return apiRequest<RegisterSessionDetail>(`/register-sessions/${sessionId}/cash-in`, {
      method: "POST",
      body: payload,
    });
  },

  cashOut(
    sessionId: string,
    payload: { amount: string; note?: string | null },
  ): Promise<RegisterSessionDetail> {
    return apiRequest<RegisterSessionDetail>(`/register-sessions/${sessionId}/cash-out`, {
      method: "POST",
      body: payload,
    });
  },
};
