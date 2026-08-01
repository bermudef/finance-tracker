import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type DashboardData } from "../api/client";
import { Badge, Card, StatCard } from "../components/ui";
import { formatCurrency } from "../lib/format";

const PIE_COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<DashboardData>("/dashboard")
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-slate-500">Loading dashboard…</p>;
  if (error) return <p className="text-sm text-red-600">Failed to load: {error}</p>;
  if (!data) return null;

  const atRiskCount = data.budgets.filter((b) => b.status === "at_risk").length;
  const overCount = data.budgets.filter((b) => b.status === "over").length;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500">Your money at a glance</p>
      </header>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Balance" value={data.total_balance} />
        <StatCard label="Net Worth" value={data.net_worth} />
        <StatCard label="Income (this month)" value={data.monthly.income} sub="vs. last month" />
        <StatCard label="Expenses (this month)" value={-data.monthly.expense} />
      </div>

      <Link
        to="/health"
        className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm transition-colors hover:border-emerald-300 hover:bg-emerald-50/40"
      >
        <div className="flex items-center gap-4">
          <div
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-lg font-bold text-white"
            style={{
              background: `conic-gradient(#10b981 ${data.health.score * 3.6}deg, #e2e8f0 0deg)`,
              color: data.health.score >= 40 ? "white" : "#0f172a",
            }}
          >
            {data.health.score}
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">Financial Health</p>
            <p className="text-xs text-slate-500">
              {data.health.grade} — six weighted signals of your money health
            </p>
          </div>
        </div>
        <span className="shrink-0 text-sm font-medium text-emerald-700">
          View details →
        </span>
      </Link>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card>
          <h2 className="mb-3 text-sm font-semibold text-slate-700">Investments</h2>
          <p className="text-2xl font-semibold tabular-nums text-slate-900">
            {formatCurrency(data.investments.total_value)}
          </p>
          <p
            className={`mt-1 text-sm font-medium tabular-nums ${
              data.investments.gain_loss >= 0 ? "text-emerald-600" : "text-red-600"
            }`}
          >
            {formatCurrency(data.investments.gain_loss, "USD", true)} ({formatCurrency(data.investments.total_cost_basis)} cost)
          </p>
        </Card>

        <Card>
          <h2 className="mb-3 text-sm font-semibold text-slate-700">Debt</h2>
          <p className="text-2xl font-semibold tabular-nums text-red-600">
            {formatCurrency(data.debt.total)}
          </p>
          <ul className="mt-2 space-y-1">
            {Object.entries(data.debt.by_type).map(([type, amount]) => (
              <li key={type} className="flex items-center justify-between text-sm text-slate-600">
                <span className="capitalize">{type.replace("_", " ")}</span>
                <span className="tabular-nums">{formatCurrency(amount)}</span>
              </li>
            ))}
            {Object.keys(data.debt.by_type).length === 0 && (
              <li className="text-sm text-slate-400">No debt 🎉</li>
            )}
          </ul>
        </Card>

        <Card>
          <h2 className="mb-3 text-sm font-semibold text-slate-700">Savings Goals</h2>
          <ul className="space-y-3">
            {data.savings_goals.map((g) => (
              <li key={g.id}>
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-slate-800">{g.name}</span>
                  <span className="tabular-nums text-slate-500">
                    {formatCurrency(g.current_amount)} / {formatCurrency(g.target_amount)}
                  </span>
                </div>
                <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full ${
                      g.progress_pct >= 100 ? "bg-emerald-500" : "bg-blue-500"
                    }`}
                    style={{ width: `${Math.min(g.progress_pct, 100)}%` }}
                  />
                </div>
              </li>
            ))}
            {data.savings_goals.length === 0 && (
              <li className="text-sm text-slate-400">No goals yet.</li>
            )}
          </ul>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Cash flow — last 6 months</h2>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={data.monthly_series}>
              <defs>
                <linearGradient id="income" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="expense" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v / 1000}k`} />
              <Tooltip formatter={(v) => formatCurrency(Number(v))} />
              <Area type="monotone" dataKey="income" stroke="#10b981" fill="url(#income)" />
              <Area type="monotone" dataKey="expense" stroke="#ef4444" fill="url(#expense)" />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Spending by category</h2>
          {data.spending_by_category.length === 0 ? (
            <p className="text-sm text-slate-400">No spending this month yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={data.spending_by_category}
                  dataKey="amount"
                  nameKey="name"
                  innerRadius={55}
                  outerRadius={90}
                  paddingAngle={2}
                >
                  {data.spending_by_category.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => formatCurrency(Number(v))} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700">Accounts</h2>
          </div>
          <ul className="divide-y divide-slate-100">
            {data.accounts.map((a) => (
              <li key={a.id} className="flex items-center justify-between py-2.5">
                <div>
                  <p className="text-sm font-medium text-slate-800">{a.name}</p>
                  <p className="text-xs capitalize text-slate-400">{a.type}</p>
                </div>
                <p className="text-sm font-semibold tabular-nums text-slate-900">
                  {formatCurrency(a.balance, a.currency)}
                </p>
              </li>
            ))}
            {data.accounts.length === 0 && (
              <li className="py-2.5 text-sm text-slate-400">No accounts yet.</li>
            )}
          </ul>
        </Card>

        <Card>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700">Budgets</h2>
            {atRiskCount > 0 && (
              <Badge tone={overCount > 0 ? "red" : "amber"}>
                {overCount > 0
                  ? `${overCount} over budget`
                  : `${atRiskCount} at risk`}
              </Badge>
            )}
          </div>
          <ul className="divide-y divide-slate-100">
            {data.budgets.map((b) => {
              const pct = b.amount > 0 ? (b.spent / b.amount) * 100 : 0;
              const over = pct > 100;
              const tone = b.status === "over" ? "red" : b.status === "at_risk" ? "amber" : "green";
              const label =
                b.status === "over" ? "Over budget" : b.status === "at_risk" ? "At risk" : "On track";
              return (
                <li key={b.id} className="py-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium text-slate-800">{b.name}</p>
                    <div className="flex items-center gap-2">
                      <span className="text-xs tabular-nums text-slate-500">
                        {formatCurrency(b.spent)} / {formatCurrency(b.amount)}
                      </span>
                      <Badge tone={tone}>{label}</Badge>
                    </div>
                  </div>
                  <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-slate-100">
                    <div
                      className={`h-full rounded-full ${over ? "bg-red-500" : "bg-emerald-500"}`}
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>
                  {b.status !== "on_track" && (
                    <p className="mt-1 text-xs text-slate-500">
                      On pace to spend{" "}
                      <span className="font-medium tabular-nums">
                        {formatCurrency(b.projected)}
                      </span>{" "}
                      this month
                      {b.status === "over" &&
                        b.amount > 0 &&
                        b.projected > b.amount && (
                          <>
                            {" "}
                            —{" "}
                            <span className="font-medium text-red-600">
                              {formatCurrency(b.projected - b.amount)} over
                            </span>
                          </>
                        )}
                    </p>
                  )}
                </li>
              );
            })}
            {data.budgets.length === 0 && (
              <li className="py-2.5 text-sm text-slate-400">No budgets yet.</li>
            )}
          </ul>
        </Card>

        <Card>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700">Upcoming bills</h2>
            <span className="text-xs text-slate-400">next 30 days</span>
          </div>
          {data.upcoming_bills.length === 0 ? (
            <p className="text-sm text-slate-400">Nothing due in the next 30 days.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {data.upcoming_bills.map((b) => {
                const soon = b.days_until <= 3;
                return (
                  <li key={b.id} className="flex items-center justify-between gap-2 py-2.5">
                    <div className="min-w-0">
                      <p className="flex items-center gap-1.5 truncate text-sm font-medium text-slate-800">
                        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${soon ? "bg-red-500" : "bg-slate-300"}`} />
                        {b.name}
                        {b.auto_pay && (
                          <span className="rounded bg-slate-100 px-1 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-500">
                            auto
                          </span>
                        )}
                      </p>
                      <p className="mt-0.5 text-xs tabular-nums text-slate-400">
                        {b.next_due_date}
                        {b.frequency !== "one-time" && ` · ${b.frequency}`}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-sm font-semibold tabular-nums text-slate-900">
                        {formatCurrency(b.amount)}
                      </p>
                      <p className={`text-xs font-medium ${soon ? "text-red-500" : "text-slate-400"}`}>
                        {b.days_until === 0
                          ? "due today"
                          : b.days_until === 1
                            ? "due tomorrow"
                            : `in ${b.days_until} days`}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
