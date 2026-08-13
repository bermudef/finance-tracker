import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Legend,
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
        <p className="text-sm text-slate-500">
          Your money at a glance. Pending transactions are excluded from balances and totals
          until they post or clear.
        </p>
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
          <p className="mb-2 text-xs text-slate-400">Includes mortgages, loans, and credit cards</p>
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
          <h2 className="mb-4 text-sm font-semibold text-slate-700">
            Cash flow — {data.current_month_series_label}
          </h2>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={data.current_month_series} margin={{ top: 4, right: 0, left: -8, bottom: 0 }}>
              <defs>
                <linearGradient id="balance" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.28} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="expense" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.24} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} />
              <YAxis
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => formatCurrency(Number(v))}
                domain={[0, "dataMax"]}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (!active || !payload?.length) return null;
                  const expense = payload.find((item) => item.dataKey === "expense");
                  const balance = payload.find((item) => item.dataKey === "balance");
                  return (
                    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-lg">
                      <p className="mb-2 text-xs font-medium text-slate-500">Day {label}</p>
                      {balance && (
                        <div className="flex items-center justify-between gap-4 text-sm">
                          <span className="text-slate-600">Remaining cash</span>
                          <span className="tabular-nums font-medium text-emerald-600">
                            {formatCurrency(Number(balance.value ?? 0))}
                          </span>
                        </div>
                      )}
                      {expense && (
                        <div className="mt-1 flex items-center justify-between gap-4 text-sm">
                          <span className="text-slate-600">Cumulative expenses</span>
                          <span className="tabular-nums font-medium text-red-600">
                            {formatCurrency(Number(expense.value ?? 0))}
                          </span>
                        </div>
                      )}
                    </div>
                  );
                }}
              />
              <Area type="monotone" dataKey="balance" name="Remaining cash" stroke="#10b981" fill="url(#balance)" strokeWidth={2} />
              <Area
                type="monotone"
                dataKey="expense"
                name="Cumulative expenses"
                stroke="#ef4444"
                fill="url(#expense)"
                strokeWidth={2}
              />
              <Legend verticalAlign="top" height={30} iconSize={10} wrapperStyle={{ paddingTop: 4, fontSize: 11 }} />
            </AreaChart>
          </ResponsiveContainer>
          <p className="mt-2 text-xs text-slate-400">
            Green shows remaining cash after posted income and expenses; red shows cumulative expenses. If the current month has no posted activity yet, the chart falls back to the latest populated month.
          </p>
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

      <Card>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">Net worth trend — last 12 months</h2>
          <span className="text-xs text-slate-400">{data.net_worth_series.note}</span>
        </div>
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={data.net_worth_series.series}>
            <defs>
              <linearGradient id="networth" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v / 1000}k`} />
            <Tooltip formatter={(v) => formatCurrency(Number(v))} />
            <Area
              type="monotone"
              dataKey="net_worth"
              name="Net worth"
              stroke="#6366f1"
              fill="url(#networth)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </Card>

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
              const limit = b.effective_amount > 0 ? b.effective_amount : b.amount;
              const pct = limit > 0 ? (b.spent / limit) * 100 : 0;
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
                        {formatCurrency(b.spent)} / {formatCurrency(limit)}
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
                  {b.rollover && b.carryover > 0 && (
                    <p className="mt-1 text-xs text-slate-500">
                      +{formatCurrency(b.carryover)} carried over from last month
                    </p>
                  )}
                  {b.status !== "on_track" && (
                    <p className="mt-1 text-xs text-slate-500">
                      On pace to spend{" "}
                      <span className="font-medium tabular-nums">
                        {formatCurrency(b.projected)}
                      </span>{" "}
                      this month
                      {b.status === "over" &&
                        limit > 0 &&
                        b.projected > limit && (
                          <>
                            {" "}
                            —{" "}
                            <span className="font-medium text-red-600">
                              {formatCurrency(b.projected - limit)} over
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

      </div>
    </div>
  );
}
