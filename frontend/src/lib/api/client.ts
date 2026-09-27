import { tokenStore } from "@/lib/auth/token-store";

/**
 * Base URL of the versioned REST API. Local development falls back to the
 * documented default so a fresh checkout runs without extra configuration.
 */
export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"
).replace(/\/+$/, "");

export type ApiErrorDetail = {
  field?: string | null;
  message: string;
};

/** The single error shape the backend returns: `{ error: { code, message, details } }`. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: ApiErrorDetail[];

  constructor(status: number, code: string, message: string, details: ApiErrorDetail[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }

  /** Validation details keyed by field, ready for `form.setError`. */
  get fieldErrors(): Record<string, string> {
    const errors: Record<string, string> = {};
    for (const detail of this.details) {
      if (detail.field && !errors[detail.field]) {
        errors[detail.field] = detail.message;
      }
    }
    return errors;
  }
}

export type RefreshedSession = {
  access_token: string;
  expires_in: number;
  /** Typed by the caller (`AuthUser`) to keep this module free of domain types. */
  user: unknown;
};

type SessionExpiredHandler = () => void;

let sessionExpiredHandler: SessionExpiredHandler | null = null;

/** Registered by `AuthProvider` so a dead session can clear app state. */
export function onSessionExpired(handler: SessionExpiredHandler | null): void {
  sessionExpiredHandler = handler;
}

let refreshInFlight: Promise<RefreshedSession | null> | null = null;

/**
 * Exchange the httpOnly refresh cookie for a new access token.
 *
 * Single-flight: concurrent callers (several 401s at once, or a page-load
 * restore racing a request) share one network round-trip. That also matters
 * because the backend rotates refresh tokens and treats a replayed one as
 * compromise, which would invalidate the whole session family.
 */
export function refreshSession(): Promise<RefreshedSession | null> {
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async (): Promise<RefreshedSession | null> => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (!response.ok) return null;
      const session = (await response.json()) as RefreshedSession;
      tokenStore.set(session.access_token);
      return session;
    } catch {
      // Network failure is indistinguishable from "no session" to the caller.
      return null;
    }
  })().finally(() => {
    refreshInFlight = null;
  });

  return refreshInFlight;
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  /** Attach the bearer token and allow a refresh-and-retry on 401. Default true. */
  auth?: boolean;
  retryOn401?: boolean;
};

async function toApiError(response: Response): Promise<ApiError> {
  let code = "unknown_error";
  let message = `The request failed with status ${response.status}.`;
  let details: ApiErrorDetail[] = [];

  try {
    const payload = (await response.json()) as {
      error?: { code?: string; message?: string; details?: ApiErrorDetail[] };
    };
    if (payload.error) {
      code = payload.error.code ?? code;
      message = payload.error.message ?? message;
      details = payload.error.details ?? [];
    }
  } catch {
    // Non-JSON body (proxy/gateway error): keep the status-based defaults.
  }

  return new ApiError(response.status, code, message, details);
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { auth = true, retryOn401 = true, body, headers: rawHeaders, ...rest } = options;

  const headers = new Headers(rawHeaders);
  if (body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (auth) {
    const token = tokenStore.get();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers,
    credentials: "include",
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 401 && auth && retryOn401) {
    // The access token is probably stale — renew it once, then replay.
    if (await refreshSession()) {
      return apiRequest<T>(path, { ...options, retryOn401: false });
    }
    // Refresh failed: the session is genuinely over.
    tokenStore.clear();
    sessionExpiredHandler?.();
    throw await toApiError(response);
  }

  if (!response.ok) throw await toApiError(response);

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}
