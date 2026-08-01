import { useMemo, useState } from "react";
import { Badge, Card, StatCard } from "../components/ui";
import { formatCurrency } from "../lib/format";

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

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <Card>
          <h2 className="text-base font-semibold text-slate-900">Debt payoff optimizer</h2>
          <p className="mt-1 text-sm text-slate-500">
            Avalanche vs. snowball comparison using your actual debts.
          </p>
          <Badge tone="blue" >Coming soon</Badge>
        </Card>
        <Card>
          <h2 className="text-base font-semibold text-slate-900">Retirement projection</h2>
          <p className="mt-1 text-sm text-slate-500">
            Monte Carlo projection toward your retirement goal.
          </p>
          <Badge tone="blue">Coming soon</Badge>
        </Card>
      </div>
    </div>
  );
}
