import { useEffect, useMemo, useState } from "react";
import {
  api,
  type MonthlyReport,
} from "../api/client";
import { Badge, Card, StatCard } from "../components/ui";
import { formatCurrency } from "../lib/format";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const CATEGORY_COLORS = [
  "#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6",
  "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16",
];

function todayValue(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(y: number, m: number): string {
  return new Date(y, m - 1, 1).toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });
}

function Delta({ current, previous }: { current: number; previous: number }) {
  if (previous === 0) return null;
  const delta = current - previous;
  const pct = (delta / Math.abs(previous)) * 100;
  const up = delta >= 0;
  return (
    <Badge tone={up ? "green" : "red"}>
      {up ? "▲" : "▼"} {Math.abs(pct).toFixed(1)}% vs last month
    </Badge>
  );
}

function formatSignedCurrency(amount: number): string {
  const formatted = formatCurrency(amount);
  return amount < 0 ? `-${formatted}` : formatted;
}

export default function StatementsPage() {
  const [month, setMonth] = useState(todayValue());
  const [report, setReport] = useState<MonthlyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const [y, m] = month.split("-").map(Number);
    api
      .get<MonthlyReport>(`/reports/monthly?year=${y}&month=${m}`)
      .then(setReport)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load report."))
      .finally(() => setLoading(false));
  }, [month]);

  const savingsRate = useMemo(() => {
    if (!report || report.income <= 0) return null;
    return ((report.income - report.expense) / report.income) * 100;
  }, [report]);

  const dailyActivity = useMemo(() => {
    if (!report) return [];
    let runningNet = 0;
    return report.daily_series.map((point) => {
      runningNet += point.income + point.expense;
      return {
        ...point,
        runningNet: Number(runningNet.toFixed(2)),
      };
    });
  }, [report]);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Monthly Statement</h1>
          <p className="text-sm text-slate-500">
            {report
              ? monthLabel(report.year, report.month)
              : "A month-by-month view of your money"}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Pending transactions are excluded until they post or clear.
          </p>
        </div>
        <input
          type="month"
          value={month}
          onChange={(e) => e.target.value && setMonth(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
        />
      </header>

      {loading && <p className="text-sm text-slate-500">Loading statement…</p>}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {report && !loading && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Income" value={report.income}>
              <Delta current={report.income} previous={report.previous.income} />
            </StatCard>
            <StatCard label="Expenses" value={-report.expense}>
              <Delta current={report.expense} previous={report.previous.expense} />
            </StatCard>
            <StatCard label="Net" value={report.net} />
            <StatCard
              label="Savings Rate"
              value={savingsRate == null ? 0 : savingsRate}
              isPercent
            />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Card>
              <h2 className="mb-4 text-sm font-semibold text-slate-700">Spending by category</h2>
              {report.by_category.length === 0 ? (
                <p className="text-sm text-slate-400">No expenses this month.</p>
              ) : (
                <ul className="space-y-3">
                  {report.by_category.map((c, i) => (
                    <li key={c.name}>
                      <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-2 font-medium text-slate-800">
                          <span
                            className="inline-block h-2.5 w-2.5 rounded-full"
                            style={{ background: CATEGORY_COLORS[i % CATEGORY_COLORS.length] }}
                          />
                          {c.name}
                        </span>
                        <span className="tabular-nums text-slate-600">
                          {formatCurrency(c.amount)}{" "}
                          <span className="text-xs text-slate-400">({c.pct}%)</span>
                        </span>
                      </div>
                      <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${Math.min(c.pct, 100)}%`,
                            background: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
                          }}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card>
              <h2 className="mb-4 text-sm font-semibold text-slate-700">By account</h2>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-400">
                    <th className="py-2 font-medium">Account</th>
                    <th className="py-2 text-right font-medium">In</th>
                    <th className="py-2 text-right font-medium">Out</th>
                    <th className="py-2 text-right font-medium">Net</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {report.by_account.map((a) => (
                    <tr key={a.id}>
                      <td className="py-2 font-medium text-slate-800">{a.name}</td>
                      <td className="py-2 text-right tabular-nums text-emerald-600">
                        {formatCurrency(a.income)}
                      </td>
                      <td className="py-2 text-right tabular-nums text-red-600">
                        {formatCurrency(a.expense)}
                      </td>
                      <td className="py-2 text-right tabular-nums text-slate-900">
                        {formatCurrency(a.net)}
                      </td>
                    </tr>
                  ))}
                  {report.by_account.length === 0 && (
                    <tr>
                      <td colSpan={4} className="py-4 text-center text-slate-400">
                        No activity this month.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>

              {report.top_merchants.length > 0 && (
                <div className="mt-6">
                  <h3 className="mb-2 text-sm font-semibold text-slate-700">Top merchants</h3>
                  <ol className="space-y-1.5">
                    {report.top_merchants.map((m) => (
                      <li
                        key={m.merchant}
                        className="flex items-center justify-between text-sm"
                      >
                        <span className="text-slate-600">{m.merchant}</span>
                        <span className="tabular-nums text-slate-800">{formatCurrency(m.amount)}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </Card>
            <Card>
              <h2 className="mb-4 text-sm font-semibold text-slate-700">Daily activity</h2>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={dailyActivity} barGap={2} barSize={8}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="day"
                    tick={{ fontSize: 10 }}
                    interval={3}
                    tickFormatter={(d) => `${d}`}
                    tickLine={false}
                    axisLine={{ stroke: "#e2e8f0" }}
                  />
                  <YAxis
                    tick={{ fontSize: 10 }}
                    tickFormatter={(v) => formatCurrency(Number(v), "USD", true)}
                    axisLine={false}
                    tickLine={false}
                    domain={["dataMin", "dataMax"]}
                  />
                  <Tooltip
                    formatter={(v, name) => [
                      formatSignedCurrency(Number(v)),
                      name === "runningNet" ? "Running net" : String(name),
                    ]}
                    labelFormatter={(d) => `Day ${d}`}
                  />
                  <ReferenceLine y={0} stroke="#e2e8f0" strokeWidth={1} />
                  <Bar dataKey="runningNet" name="Running net" radius={[2, 2, 2, 2]}>
                    {dailyActivity.map((point) => (
                      <Cell key={point.day} fill={point.runningNet >= 0 ? "#10b981" : "#ef4444"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <p className="mt-2 text-xs text-slate-400">
                A running month-to-date histogram: income lifts the bars, and expenses pull
                them down over time.
              </p>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
