const API_BASE = "/api/v1";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// ---- token storage (localStorage for demo simplicity; HttpOnly cookies in prod) ----
const ACCESS_KEY = "ft_access_token";
const REFRESH_KEY = "ft_refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function storeTokens(t: AuthTokens): void {
  localStorage.setItem(ACCESS_KEY, t.access_token);
  localStorage.setItem(REFRESH_KEY, t.refresh_token);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  retry = true
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 && retry) {
    // Attempt one refresh-token retry before failing.
    const refreshed = await refreshAccessToken();
    if (refreshed) return request<T>(path, options, false);
  }

  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail =
      typeof body?.detail === "string"
        ? body.detail
        : Array.isArray(body?.detail)
          ? body.detail.map((d: { msg?: string }) => d.msg ?? "").join(", ")
          : `Request failed (${res.status})`;
    throw new ApiError(res.status, detail);
  }
  return body as T;
}

async function refreshAccessToken(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) {
      clearTokens();
      return false;
    }
    const tokens = (await res.json()) as AuthTokens;
    storeTokens(tokens);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

// ---- typed domain models ----
export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
}

export interface Account {
  id: number;
  name: string;
  type: string;
  currency: string;
  opening_balance: number;
  is_active: boolean;
}

export interface Category {
  id: number;
  name: string;
  type: string;
  color: string | null;
  parent_id: number | null;
}

export interface Transaction {
  id: number;
  account_id: number;
  category_id: number | null;
  date: string;
  amount: number;
  description: string | null;
  merchant: string | null;
  status: string;
  account_name?: string | null;
  category_name?: string | null;
}

export interface Budget {
  id: number;
  category_id: number | null;
  name: string;
  amount: number;
  period: string;
}

export interface DashboardData {
  total_balance: number;
  accounts: Array<Account & { balance: number }>;
  monthly: {
    income: number;
    expense: number;
    net: number;
    last_month_income: number;
    last_month_expense: number;
  };
  spending_by_category: Array<{ name: string; amount: number; color: string | null }>;
  monthly_series: Array<{ month: string; income: number; expense: number }>;
  budgets: Array<Budget & { spent: number }>;
}
