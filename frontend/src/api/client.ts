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
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

export interface ImportResult {
  created: number;
  skipped: number;
  errors: { row: number; error: string }[];
}

/** Download transactions as CSV (triggered by an <a download> after fetching). */
export async function exportTransactionsCsv(): Promise<Blob> {
  const token = getAccessToken();
  const res = await fetch(`${API_BASE}/transactions/export`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new ApiError(res.status, `Export failed (${res.status})`);
  return res.blob();
}

/** Upload a CSV file and return per-row import results. */
export async function importTransactionsCsv(file: File): Promise<ImportResult> {
  const token = getAccessToken();
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/transactions/import`, {
    method: "POST",
    body: form,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    throw new ApiError(
      res.status,
      typeof body?.detail === "string" ? body.detail : `Import failed (${res.status})`
    );
  }
  return body as ImportResult;
}

/** Download a CSV export as a Blob (fetch with auth, no JSON parsing). */
async function exportCsvBlob(path: string): Promise<Blob> {
  const token = getAccessToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new ApiError(res.status, `Export failed (${res.status})`);
  return res.blob();
}

/** Trigger a browser download of a CSV export endpoint. */
export async function downloadCsv(path: string, filename: string): Promise<void> {
  const blob = await exportCsvBlob(path);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ---- typed domain models ----
export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  email_verified: boolean;
}

export interface RegisterResponse extends AuthTokens {
  email_verified: boolean;
  verification_token: string | null;
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
  rollover: boolean;
}

export interface RecurringTransactionItem {
  id: number;
  user_id: number;
  account_id: number;
  category_id: number | null;
  name: string;
  amount: number;
  frequency: "weekly" | "monthly" | "yearly";
  next_date: string;
  is_active: boolean;
  notes: string | null;
  created_at: string;
}

export interface BenchmarkResult {
  years: number;
  user_return_pct: number;
  benchmark_return_pct: number;
  start_month: string;
  end_month: string;
  series: Array<{ month: string; index: number }>;
  note: string;
}

export interface LossHarvestingCandidate {
  name: string;
  symbol: string | null;
  type: string;
  cost_basis: number;
  current_value: number;
  unrealized_loss: number;
  est_tax_savings: number;
}

export interface LossHarvestingResult {
  candidates: LossHarvestingCandidate[];
  note: string;
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
  budgets: Array<
    Budget & {
      spent: number;
      progress_pct: number;
      projected: number;
      status: "on_track" | "at_risk" | "over";
      days_elapsed: number;
      days_in_month: number;
      carryover: number;
      effective_amount: number;
      available: number;
    }
  >;
  net_worth: number;
  net_worth_series: {
    months: number;
    series: Array<{ month: string; net_worth: number }>;
    investments_value: number;
    debt_total: number;
    note: string;
  };
  investments: {
    total_value: number;
    total_cost_basis: number;
    gain_loss: number;
  };
  debt: {
    total: number;
    by_type: Record<string, number>;
  };
  savings_goals: Array<{
    id: number;
    name: string;
    target_amount: number;
    current_amount: number;
    progress_pct: number;
    target_date: string | null;
  }>;
  upcoming_bills: Array<{
    id: number;
    name: string;
    amount: number;
    frequency: string;
    auto_pay: boolean;
    next_due_date: string;
    days_until: number;
  }>;
  health: { score: number; grade: "Excellent" | "Good" | "Fair" | "Needs work" };
}

export interface MonthlyReport {
  year: number;
  month: number;
  income: number;
  expense: number;
  net: number;
  previous: { income: number; expense: number };
  by_category: Array<{ name: string; amount: number; pct: number }>;
  by_account: Array<{ id: number; name: string; income: number; expense: number; net: number }>;
  top_merchants: Array<{ merchant: string; amount: number }>;
  daily_series: Array<{ day: number; income: number; expense: number }>;
}

export interface HealthSubscore {
  key: string;
  label: string;
  score: number;
  weight: number;
  detail: string;
}

export interface HealthRecommendation {
  key: string;
  text: string;
}

export interface HealthScore {
  score: number;
  grade: "Excellent" | "Good" | "Fair" | "Needs work";
  as_of: string;
  period_label: string;
  subscores: HealthSubscore[];
  recommendations: HealthRecommendation[];
}

export interface DebtPayoffSimulation {
  months_to_debt_free: number | null;
  total_interest: number;
  payoff_order: Array<{ name: string; months: number }>;
  timeline: Array<{ month: number; remaining: number }>;
  did_not_converge: boolean;
}

export interface DebtPayoffResult {
  extra_monthly: number;
  total_principal: number;
  debt_count: number;
  avalanche: DebtPayoffSimulation;
  snowball: DebtPayoffSimulation;
  interest_savings: number | null;
  months_faster: number | null;
}

export interface CreditCard {
  id: number;
  name: string;
  balance: number;
  credit_limit: number;
  apr: number;
  payment_due_date: string | null;
  min_payment: number | null;
  is_active: boolean;
}

export interface Debt {
  id: number;
  name: string;
  type: string;
  principal: number;
  interest_rate: number;
  min_payment: number | null;
  payment_due_date: string | null;
  remaining_term_months: number | null;
  is_active: boolean;
}

export interface Investment {
  id: number;
  name: string;
  type: string;
  symbol: string | null;
  cost_basis: number;
  current_value: number;
  account_name: string | null;
  notes: string | null;
}

export interface SavingsGoal {
  id: number;
  name: string;
  target_amount: number;
  current_amount: number;
  target_date: string | null;
  is_active: boolean;
  notes: string | null;
}

export interface Bill {
  id: number;
  name: string;
  amount: number;
  due_date: string;
  frequency: string;
  auto_pay: boolean;
  is_active: boolean;
  notes: string | null;
}

export interface RetirementProjectionPoint {
  age: number;
  p10: number;
  p25: number;
  median: number;
  p75: number;
  p90: number;
}

export interface RetirementProjectionSummary {
  median_nominal: number;
  median_real: number;
  p10_nominal: number;
  p90_nominal: number;
}

export interface RetirementProjectionResult {
  years_to_retirement: number;
  series: RetirementProjectionPoint[];
  summary: RetirementProjectionSummary;
}

export interface BudgetForecastEntry {
  category: string;
  predicted: number;
  p10: number;
  p90: number;
  budget: number | null;
  will_exceed: boolean;
  confidence: "high" | "medium" | "low";
  months_of_data: number;
}

export interface BudgetForecastResult {
  forecasts: BudgetForecastEntry[];
  flagged: BudgetForecastEntry[];
  total_forecast: number;
  total_budget: number;
}

export interface NotificationItem {
  id: number;
  user_id: number;
  title: string;
  message: string;
  type: string;
  read: boolean;
  created_at: string;
}

export interface Household {
  id: number;
  name: string;
  created_by: number;
  created_at: string;
}

export interface HouseholdMember {
  id: number;
  household_id: number;
  user_id: number;
  role: "owner" | "admin" | "member";
  joined_at: string;
  email: string;
}

export interface HouseholdInvite {
  id: number;
  household_id: number;
  email: string;
  role: string;
  created_at: string;
  expires_at: string;
  accepted_at: string | null;
}

export interface PendingHouseholdInvite {
  id: number;
  household_id: number;
  household_name: string;
  email: string;
  role: string;
  token: string;
  created_at: string;
  expires_at: string;
}

export const notificationsApi = {
  list: () => api.get<NotificationItem[]>("/notifications"),
  generate: () => api.post<NotificationItem[]>("/notifications/generate"),
  markRead: (id: number) => api.patch<{ status: string }>(`/notifications/${id}/read`, {}),
  markAllRead: () => api.patch<{ status: string; marked: number }>("/notifications/read-all", {}),
  remove: (id: number) => api.delete<{ status: string }>(`/notifications/${id}`),
};

export const householdsApi = {
  list: () => api.get<Household[]>("/households"),
  create: (name: string) => api.post<Household>("/households", { name }),
  members: (householdId: number) => api.get<HouseholdMember[]>(`/households/${householdId}/members`),
  invites: (householdId: number) => api.get<HouseholdInvite[]>(`/households/${householdId}/invites`),
  createInvite: (householdId: number, email: string, role: string) =>
    api.post<HouseholdInvite>(`/households/${householdId}/invites`, { email, role }),
  cancelInvite: (householdId: number, inviteId: number) =>
    api.delete<{ status: string }>(`/households/${householdId}/invites/${inviteId}`),
  pending: () => api.get<PendingHouseholdInvite[]>("/households/invites/pending"),
  accept: (token: string) =>
    api.get<{ status: string; household_id: number }>(`/households/invites/accept?token=${encodeURIComponent(token)}`),
};

export const recurringApi = {
  list: () => api.get<RecurringTransactionItem[]>("/recurring-transactions"),
  create: (data: {
    name: string;
    account_id: number;
    category_id: number | null;
    amount: number;
    frequency: string;
    next_date: string;
    notes?: string | null;
  }) => api.post<RecurringTransactionItem>("/recurring-transactions", data),
  update: (id: number, data: Partial<RecurringTransactionItem>) =>
    api.put<RecurringTransactionItem>(`/recurring-transactions/${id}`, data),
  remove: (id: number) => api.delete<{ status: string }>(`/recurring-transactions/${id}`),
  process: () =>
    api.post<{ posted: number; message: string }>("/recurring-transactions/process"),
};

export const investmentsApi = {
  benchmark: (years: number) =>
    api.get<BenchmarkResult>(`/investments/benchmark?years=${years}`),
};

export const toolsApi = {
  lossHarvesting: () => api.get<LossHarvestingResult>("/tools/loss-harvesting"),
};

export const authApi = {
  register: (data: { email: string; password: string; full_name?: string }) =>
    api.post<RegisterResponse>("/auth/register", data),
  verifyEmail: (token: string) =>
    api.get<{ status: string; email: string }>(
      `/auth/verify-email?token=${encodeURIComponent(token)}`
    ),
};
