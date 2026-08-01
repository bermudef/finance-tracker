import { useEffect, useMemo, useState } from "react";
import {
  api,
  type Debt,
  type DebtPayoffResult,
  type RetirementProjectionResult,
  type BudgetForecastResult,
} from "../api/client";
import { Badge, Card, StatCard } from "../components/ui";
import { formatCurrency } from "../lib/format";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const DEFAULT_INPUTS = {
  annualIncome: 120000,
  monthlyDebts: 500,
  downPaymentPct: 20,
  interestRate: 6.5,
  loanTermYears: 30,
  propertyTaxRate: 1.2,
  annualInsurance: 1500,
  monthlyHoa: 0,
};

type Inputs = typeof DEFAULT_INPUTS;

const NUMBERS: Record<keyof Inputs, string> = {
  annualIncome: "Gross annual income ($)",
  monthlyDebts: "Monthly debt payments ($)",
  downPaymentPct: "Down payment (%)",
  interestRate: "Interest rate (%)",
  loanTermYears: "Loan term (years)",
  propertyTaxRate: "Property tax rate (%/yr)",
  annualInsurance: "Annual insurance ($)",
  monthlyHoa: "Monthly HOA ($)",
};

function compute(inputs: Inputs) {
  const {
    annualIncome, monthlyDebts, downPaymentPct, interestRate,
    loanTermYears, propertyTaxRate, annualInsurance, monthlyHoa,
  } = inputs;

  const monthlyGross = annualIncome / 12;
  const frontEndCap = monthlyGross * 0.28; // housing <= 28% of gross income
  const backEndCap = monthlyGross * 0.36 - monthlyDebts; // total debt <= 36%
  const housingBudget = Math.max(0, Math.min(frontEndCap, backEndCap));
  const binding = frontEndCap <= backEndCap ? "front" : "back";

  // Taxes/insurance scale with price, and price depends on the loan — solve
  // with a few fixed-point iterations (converges within 3 passes in practice).
  const r = interestRate / 100 / 12;
  const n = loanTermYears * 12;
  let loan = 0;
  let price = 0;
  for (let i = 0; i < 5; i++) {
    const tax = (propertyTaxRate / 100) * price / 12;
    const insurance = annualInsurance / 12;
    const pAndI = Math.max(0, housingBudget - tax - insurance - monthlyHoa);
    loan = r === 0 ? pAndI * n : (pAndI * (1 - Math.pow(1 + r, -n))) / r;
    price = downPaymentPct >= 100 ? 0 : loan / (1 - downPaymentPct / 100);
  }
  const downPayment = price * (downPaymentPct / 100);
  const totalMonthly =
    (r === 0 ? loan / Math.max(n, 1) : (loan * r) / (1 - Math.pow(1 + r, -n))) +
    (propertyTaxRate / 100) * price / 12 +
    annualInsurance / 12 +
    monthlyHoa;

  return {
    maxPrice: price,
    maxLoan: loan,
    downPayment,
    monthlyPI: (r === 0 ? loan / Math.max(n, 1) : (loan * r) / (1 - Math.pow(1 + r, -n))),
    monthlyTax: (propertyTaxRate / 100) * price / 12,
    monthlyInsurance: annualInsurance / 12,
    monthlyHoa,
    totalMonthly,
    binding,
    dti: monthlyGross > 0 ? ((monthlyDebts + totalMonthly) / monthlyGross) * 100 : 0,
    feasible: price > 0 && totalMonthly > 0,
  };
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <input
        type="number"
        value={Number.isNaN(value) ? "" : value}
        onChange={(e) => onChange(e.target.value === "" ? NaN : Number(e.target.value))}
        className="rounded-lg border border-slate-300 px-3 py-2 text-sm tabular-nums focus:border-emerald-500 focus:outline-none"
      />
    </label>
  );
}

function StrategySummary({ sim, title, tone }: { sim: DebtPayoffResult["avalanche"]; title: string; tone: "emerald" | "blue" }) {
  const months = sim.months_to_debt_free;
  const years = months ? Math.floor(months / 12) : 0;
  const rem = months ? months % 12 : 0;
  return (
    <div className={`rounded-lg border p-4 ${tone === "emerald" ? "border-emerald-200 bg-emerald-50/50" : "border-blue-200 bg-blue-50/50"}`}>
      <p className="text-sm font-semibold text-slate-800">{title}</p>
      <p className="mt-2 text-xs text-slate-500">Debt-free in</p>
      <p className="text-xl font-semibold tabular-nums text-slate-900">
        {months == null ? "—" : `${years}y ${rem}m`}
      </p>
      <p className="mt-1 text-xs text-slate-500">Total interest</p>
      <p className="text-xl font-semibold tabular-nums text-slate-900">
        {formatCurrency(sim.total_interest)}
      </p>
      <ol className="mt-3 space-y-1">
        {sim.payoff_order.map((p) => (
          <li key={p.name} className="flex items-center justify-between text-xs">
            <span className="truncate text-slate-600">{p.name}</span>
            <span className="ml-2 shrink-0 tabular-nums text-slate-400">
              month {p.months}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function DebtPayoffTool() {
  const [debts, setDebts] = useState<Debt[] | null>(null);
  const [extra, setExtra] = useState(200);
  const [result, setResult] = useState<DebtPayoffResult | null>(null);
  const [loading, setLoading] = useState(true);

  // Merged timeline for the chart, keyed by month so both strategies line up.
  const chartData = useMemo(() => {
    if (!result) return [];
    const map = new Map<number, { month: number; avalanche: number; snowball: number }>();
    for (const pt of result.avalanche.timeline) {
      const row = map.get(pt.month) ?? { month: pt.month, avalanche: 0, snowball: 0 };
      row.avalanche = pt.remaining;
      map.set(pt.month, row);
    }
    for (const pt of result.snowball.timeline) {
      const row = map.get(pt.month) ?? { month: pt.month, avalanche: 0, snowball: 0 };
      row.snowball = pt.remaining;
      map.set(pt.month, row);
    }
    return Array.from(map.values()).sort((a, b) => a.month - b.month);
  }, [result]);

  useEffect(() => {
    api
      .get<Debt[]>("/debts")
      .then((d) => setDebts(d.filter((x) => x.is_active && x.principal > 0)))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!debts || debts.length === 0) return;
    api
      .post<DebtPayoffResult>("/tools/debt-payoff", { extra_monthly: extra })
      .then(setResult)
      .catch((err) => console.error(err));
  }, [debts, extra]);

  if (loading) return <p className="text-sm text-slate-500">Loading debts…</p>;

  if (debts && debts.length === 0) {
    return (
      <Card>
        <h2 className="text-base font-semibold text-slate-900">Debt payoff optimizer</h2>
        <p className="mt-1 text-sm text-slate-500">
          Compare avalanche (highest APR first) vs. snowball (smallest balance
          first) with your real debts.
        </p>
        <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">
          No active debts yet —{" "}
          <a href="/debts" className="font-medium text-emerald-700 hover:underline">
            add your debts
          </a>{" "}
          to see the comparison.
        </p>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Debt payoff optimizer</h2>
          <p className="mt-1 text-sm text-slate-500">
            {result?.debt_count ?? 0} debts · {formatCurrency(result?.total_principal ?? 0)} total
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          Extra payment
          <input
            type="number"
            min={0}
            value={extra}
            onChange={(e) => setExtra(Math.max(0, Number(e.target.value) || 0))}
            className="w-28 rounded-lg border border-slate-300 px-3 py-2 text-sm tabular-nums focus:border-emerald-500 focus:outline-none"
          />
          <span className="text-xs text-slate-400">/mo</span>
        </label>
      </div>

      {result && (
        <>
          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StrategySummary sim={result.avalanche} title="Avalanche" tone="emerald" />
            <StrategySummary sim={result.snowball} title="Snowball" tone="blue" />
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-sm font-semibold text-slate-800">Winner</p>
              {result.interest_savings == null || result.interest_savings <= 0 ? (
                <>
                  <p className="mt-2 text-xl font-semibold text-slate-900">Dead heat</p>
                  <p className="mt-1 text-xs text-slate-500">
                    Both strategies cost the same. Pick whichever keeps you motivated.
                  </p>
                </>
              ) : (
                <>
                  <p className="mt-2 text-xl font-semibold text-emerald-700">
                    Avalanche saves {formatCurrency(result.interest_savings)}
                  </p>
                  {result.months_faster ? (
                    <p className="mt-1 text-xs text-slate-500">
                      and reaches debt-free{" "}
                      {Math.floor(result.months_faster / 12)}y {result.months_faster % 12}m sooner.
                    </p>
                  ) : (
                    <p className="mt-1 text-xs text-slate-500">
                      Snowball stays motivated with faster early wins.
                    </p>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="mt-6">
            <h3 className="mb-2 text-sm font-semibold text-slate-700">Remaining debt over time</h3>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${v / 1000}k`} />
                <Tooltip formatter={(v) => formatCurrency(Number(v))} />
                <Legend />
                <Line type="monotone" dataKey="avalanche" name="Avalanche" stroke="#10b981" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="snowball" name="Snowball" stroke="#3b82f6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </Card>
  );
}

function RetirementTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm">
      <p className="text-xs font-semibold text-slate-500">Age {label}</p>
      {payload.map((entry: any, i: number) => (
        <p key={i} className="text-xs tabular-nums" style={{ color: entry.color }}>
          {entry.name}: {formatCurrency(Number(entry.value))}
        </p>
      ))}
    </div>
  );
}

function RetirementTool() {
  const [inputs, setInputs] = useState({
    currentAge: 30,
    retirementAge: 65,
    currentBalance: 50000,
    monthlyContribution: 1000,
    expectedReturn: 7.0,
    inflationRate: 2.5,
    stdDev: 12.0,
  });
  const [result, setResult] = useState<RetirementProjectionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    timer = setTimeout(() => {
      setLoading(true);
      setError(null);
      api
        .post<RetirementProjectionResult>("/tools/retirement-projection", inputs)
        .then(setResult)
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    }, 300);
    return () => clearTimeout(timer);
  }, [inputs]);

  const set = (key: keyof typeof inputs) => (v: number) =>
    setInputs((prev) => ({ ...prev, [key]: v }));

  const chartData = useMemo(() => result?.series ?? [], [result]);

  return (
    <Card>
      <h2 className="text-base font-semibold text-slate-900">
        Retirement projection
      </h2>
      <p className="mt-1 text-sm text-slate-500">
        Monte Carlo simulation (2,000 paths) showing the distribution of your
        retirement balance at each age.
      </p>

      <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-500">Current age</span>
          <input
            type="number"
            min={18}
            max={100}
            value={inputs.currentAge}
            onChange={(e) => set("currentAge")(Number(e.target.value) || 0)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm tabular-nums focus:border-emerald-500 focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-500">Retirement age</span>
          <input
            type="number"
            min={18}
            max={100}
            value={inputs.retirementAge}
            onChange={(e) => set("retirementAge")(Number(e.target.value) || 0)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm tabular-nums focus:border-emerald-500 focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-500">Current balance ($)</span>
          <input
            type="number"
            min={0}
            step={1000}
            value={inputs.currentBalance}
            onChange={(e) => set("currentBalance")(Number(e.target.value) || 0)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm tabular-nums focus:border-emerald-500 focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-500">Monthly contribution ($)</span>
          <input
            type="number"
            min={0}
            step={100}
            value={inputs.monthlyContribution}
            onChange={(e) => set("monthlyContribution")(Number(e.target.value) || 0)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm tabular-nums focus:border-emerald-500 focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-500">Expected return (%)</span>
          <input
            type="number"
            step={0.1}
            value={inputs.expectedReturn}
            onChange={(e) => set("expectedReturn")(Number(e.target.value) || 0)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm tabular-nums focus:border-emerald-500 focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-500">Inflation rate (%)</span>
          <input
            type="number"
            step={0.1}
            value={inputs.inflationRate}
            onChange={(e) => set("inflationRate")(Number(e.target.value) || 0)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm tabular-nums focus:border-emerald-500 focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-500">Annual volatility (%)</span>
          <input
            type="number"
            step={0.1}
            value={inputs.stdDev}
            onChange={(e) => set("stdDev")(Number(e.target.value) || 0)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm tabular-nums focus:border-emerald-500 focus:outline-none"
          />
        </label>
      </div>

      {loading && <p className="mt-4 text-sm text-slate-400">Running simulation…</p>}
      {error && (
        <p className="mt-4 text-sm text-red-600">Simulation failed: {error}</p>
      )}

      {result && !loading && (
        <>
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Years to retirement" value={result.years_to_retirement} format="number" />
            <StatCard label="Median balance (nominal)" value={result.summary.median_nominal} />
            <StatCard label="P10 (conservative)" value={result.summary.p10_nominal} />
            <StatCard label="P90 (optimistic)" value={result.summary.p90_nominal} />
          </div>

           <div className="mt-6">
            <h3 className="mb-2 text-sm font-semibold text-slate-700">
              Balance distribution by age
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="age" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${v / 1000}k`} />
                <Tooltip content={<RetirementTooltip />} />
                <Legend />

                {/* Key percentile lines */}
                <Line
                  type="monotone"
                  dataKey="median"
                  name="Median"
                  stroke="#065f46"
                  strokeWidth={2.5}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="p10"
                  name="P10"
                  stroke="#ef4444"
                  strokeWidth={1}
                  dot={false}
                  strokeDasharray="4 2"
                />
                <Line
                  type="monotone"
                  dataKey="p90"
                  name="P90"
                  stroke="#10b981"
                  strokeWidth={1}
                  dot={false}
                  strokeDasharray="6 3"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </Card>
  );
}

function BudgetForecastTool() {
  const [result, setResult] = useState<BudgetForecastResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>
    timer = setTimeout(() => {
      setLoading(true)
      setError(null)
      api
        .post<BudgetForecastResult>("/tools/budget-forecast", { months_back: 6 })
        .then(setResult)
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false))
    }, 300)
    return () => clearTimeout(timer)
  }, [])

  if (loading) return <p className="text-sm text-slate-400">Forecasting…</p>
  if (error) return <p className="text-sm text-red-600">Forecast failed: {error}</p>
  if (!result) return null

  return (
    <Card>
      <h2 className="text-base font-semibold text-slate-900">Budget forecast</h2>
      <p className="mt-1 text-sm text-slate-500">
        Weighted moving average of the last 6 months. Categories projected to
        exceed their budget are flagged.
      </p>

      {result.forecasts.length === 0 ? (
        <p className="mt-4 text-sm text-slate-400">
          No budget or spending data yet — add budgets and transactions to see
          forecasts.
        </p>
      ) : (
        <>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Total forecast" value={result.total_forecast} />
            <StatCard label="Total budget" value={result.total_budget} />
            <StatCard
              label="Over budget"
              value={result.flagged.length}
              positive={false}
            />
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full max-w-2xl text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
                  <th className="pb-2 font-medium">Category</th>
                  <th className="pb-2 font-medium text-right">Forecast</th>
                  <th className="pb-2 font-medium text-right">P90</th>
                  <th className="pb-2 font-medium text-right">Budget</th>
                  <th className="pb-2 font-medium text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {result.forecasts.map((f) => (
                  <tr key={f.category} className="py-2">
                    <td className="py-2 font-medium text-slate-800">
                      {f.category}
                    </td>
                    <td className="py-2 text-right tabular-nums text-slate-900">
                      {formatCurrency(f.predicted)}
                    </td>
                    <td className="py-2 text-right tabular-nums text-slate-500">
                      {formatCurrency(f.p90)}
                    </td>
                    <td className="py-2 text-right tabular-nums text-slate-900">
                      {f.budget != null ? formatCurrency(f.budget) : "—"}
                    </td>
                    <td className="py-2 text-center">
                      {f.will_exceed ? (
                        <Badge tone="red">Over budget</Badge>
                      ) : f.budget != null ? (
                        <Badge tone="green">On track</Badge>
                      ) : (
                        <Badge tone="slate">No budget</Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Card>
  )
}

export default function ToolsPage() {
  const [inputs, setInputs] = useState<Inputs>(DEFAULT_INPUTS);
  const result = useMemo(() => compute(inputs), [inputs]);

  const set = (key: keyof Inputs) => (v: number) =>
    setInputs((prev) => ({ ...prev, [key]: v }));

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Financial Tools</h1>
        <p className="text-sm text-slate-500">Calculators to help you plan big decisions</p>
      </header>

      <DebtPayoffTool />

      <RetirementTool />

      <BudgetForecastTool />

      <Card>
        <h2 className="text-base font-semibold text-slate-900">How much house can I afford?</h2>
        <p className="mt-1 text-sm text-slate-500">
          Uses the lender 28/36 rule: housing costs ≤ 28% of gross income, and total
          debt payments ≤ 36%. Taxes, insurance, and HOA are included in the housing budget.
        </p>

        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Object.keys(NUMBERS).map((key) => (
            <NumberField
              key={key}
              label={NUMBERS[key as keyof Inputs]}
              value={inputs[key as keyof Inputs]}
              onChange={set(key as keyof Inputs)}
            />
          ))}
        </div>

        {!result.feasible && (
          <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Based on these numbers, there is no price where the monthly housing payment
            fits inside the 28/36 limits. Try increasing your income or down payment, or
            reducing existing debts.
          </div>
        )}

        {result.feasible && (
          <div className="mt-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard label="Max home price" value={result.maxPrice} positive={false} />
              <StatCard label="Max loan amount" value={result.maxLoan} positive={false} />
              <StatCard label="Down payment" value={result.downPayment} positive={false} />
              <StatCard label="Total monthly payment" value={result.totalMonthly} positive={false} />
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <Badge tone={result.binding === "back" ? "red" : "green"}>
                {result.binding === "back"
                  ? "Limited by your debt-to-income ratio (36% back-end rule)"
                  : "Limited by the 28% housing-cost rule"}
              </Badge>
              <span className="text-sm text-slate-500">
                Projected DTI after purchase: {result.dti.toFixed(1)}%
              </span>
            </div>

            <div className="mt-5 overflow-x-auto">
              <table className="w-full max-w-md text-sm">
                <tbody className="divide-y divide-slate-100">
                  <tr>
                    <td className="py-2 text-slate-500">Principal & interest</td>
                    <td className="py-2 text-right font-medium tabular-nums text-slate-800">
                      {formatCurrency(result.monthlyPI)}/mo
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 text-slate-500">Property tax</td>
                    <td className="py-2 text-right font-medium tabular-nums text-slate-800">
                      {formatCurrency(result.monthlyTax)}/mo
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 text-slate-500">Insurance</td>
                    <td className="py-2 text-right font-medium tabular-nums text-slate-800">
                      {formatCurrency(result.monthlyInsurance)}/mo
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 text-slate-500">HOA</td>
                    <td className="py-2 text-right font-medium tabular-nums text-slate-800">
                      {formatCurrency(result.monthlyHoa)}/mo
                    </td>
                  </tr>
                  <tr className="border-t border-slate-200 font-semibold text-slate-900">
                    <td className="py-2">Total</td>
                    <td className="py-2 text-right tabular-nums">
                      {formatCurrency(result.totalMonthly)}/mo
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            {result.downPayment < result.maxPrice * 0.2 && (
              <p className="mt-3 text-xs text-amber-700">
                Below 20% down — expect PMI (private mortgage insurance) until you reach 20% equity.
              </p>
            )}
          </div>
        )}
       </Card>
     </div>
   );
}
