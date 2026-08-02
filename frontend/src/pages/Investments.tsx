import { useCallback, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ResourcePage, { money } from "../components/ResourcePage";
import { investmentsApi, type BenchmarkResult } from "../api/client";
import { Card } from "../components/ui";

const INVESTMENT_TYPES = [
  { value: "stock", label: "Stock" },
  { value: "etf", label: "ETF" },
  { value: "retirement", label: "Retirement" },
  { value: "crypto", label: "Crypto" },
  { value: "cash", label: "Cash" },
  { value: "other", label: "Other" },
];

const WINDOWS = [
  { value: 1, label: "1Y" },
  { value: 3, label: "3Y" },
  { value: 5, label: "5Y" },
  { value: 10, label: "10Y" },
];

export default function InvestmentsPage() {
  return (
    <>
      <ResourcePage
        title="Investments"
        description="Stocks, ETFs, and retirement accounts"
        path="/investments"
        fields={[
          { key: "name", label: "Name", type: "text", required: true },
          { key: "type", label: "Type", type: "select", required: true, options: INVESTMENT_TYPES, defaultValue: "other" },
          { key: "symbol", label: "Symbol", type: "text", placeholder: "VTI" },
          { key: "cost_basis", label: "Cost Basis", type: "number", defaultValue: 0, render: money },
          { key: "current_value", label: "Current Value", type: "number", defaultValue: 0, render: money },
          { key: "account_name", label: "Account", type: "text", placeholder: "Fidelity 401k" },
          { key: "notes", label: "Notes", type: "textarea", hideInTable: true },
        ]}
      />
      <BenchmarkCard />
    </>
  );
}

function BenchmarkCard() {
  const [years, setYears] = useState(5);
  const [data, setData] = useState<BenchmarkResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (windowYears: number) => {
    setLoading(true);
    setError(null);
    try {
      setData(await investmentsApi.benchmark(windowYears));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load benchmark");
    } finally {
      setLoading(false);
    }
  }, []);

  // Load on mount and whenever the selected window changes.
  useEffect(() => {
    void load(years);
  }, [years, load]);

  return (
    <Card>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-700">
            vs. S&P 500 <span className="font-normal text-slate-400">({data?.start_month} → {data?.end_month})</span>
          </h2>
          <p className="mt-0.5 text-xs text-slate-400">
            Your total return on cost basis vs. the index (100 at start)
          </p>
        </div>
        <div className="flex gap-1 rounded-lg border border-slate-200 p-0.5">
          {WINDOWS.map((w) => (
            <button
              key={w.value}
              onClick={() => setYears(w.value)}
              className={`rounded-md px-3 py-1 text-xs font-semibold ${
                years === w.value ? "bg-emerald-600 text-white" : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="py-8 text-center text-sm text-slate-400">Loading benchmark…</p>
      ) : error ? (
        <p className="py-8 text-center text-sm text-red-600">{error}</p>
      ) : data ? (
        <>
          <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Stat label="Your return" value={`${data.user_return_pct}%`} tone={data.user_return_pct >= 0 ? "green" : "red"} />
            <Stat label="S&P 500" value={`${data.benchmark_return_pct}%`} tone="blue" />
            <Stat
              label="Difference"
              value={`${(data.user_return_pct - data.benchmark_return_pct).toFixed(2)}%`}
              tone={data.user_return_pct >= data.benchmark_return_pct ? "green" : "red"}
            />
            <Stat label="Window" value={`${data.years}Y`} tone="slate" />
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={data.series}>
              <defs>
                <linearGradient id="spx" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} minTickGap={30} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}`} />
              <Tooltip formatter={(v) => `${v}`} />
              <Area
                type="monotone"
                dataKey="index"
                name="S&P 500"
                stroke="#3b82f6"
                strokeWidth={2}
                fill="url(#spx)"
              />
            </AreaChart>
          </ResponsiveContainer>
          <p className="mt-2 text-xs text-slate-400">{data.note}</p>
        </>
      ) : null}
    </Card>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone: "green" | "red" | "blue" | "slate" }) {
  const tones = {
    green: "text-emerald-600",
    red: "text-red-600",
    blue: "text-blue-600",
    slate: "text-slate-700",
  };
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-lg font-semibold tabular-nums ${tones[tone]}`}>{value}</p>
    </div>
  );
}
