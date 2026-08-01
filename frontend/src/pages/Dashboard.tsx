import { useEffect, useState } from "react";
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

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500">Your money at a glance</p>
      </header>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Balance" value={data.total_balance} />
        <StatCard label="Income (this month)" value={data.monthly.income} sub="vs. last month" />
        <StatCard label="Expenses (this month)" value={-data.monthly.expense} />
        <StatCard label="Net (this month)" value={data.monthly.net} />
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Accounts</h2>
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
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Budgets</h2>
          <ul className="divide-y divide-slate-100">
            {data.budgets.map((b) => {
              const pct = b.amount > 0 ? (b.spent / b.amount) * 100 : 0;
              const over = pct > 100;
              return (
                <li key={b.id} className="py-2.5">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-slate-800">{b.name}</p>
                    <p className="text-xs tabular-nums text-slate-500">
                      {formatCurrency(b.spent)} / {formatCurrency(b.amount)}
                    </p>
                  </div>
                  <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-slate-100">
                    <div
                      className={`h-full rounded-full ${over ? "bg-red-500" : "bg-emerald-500"}`}
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>
                  {over && <Badge tone="red">Over budget</Badge>}
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
