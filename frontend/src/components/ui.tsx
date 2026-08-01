import type { ReactNode } from "react";
import { formatCurrency } from "../lib/format";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

export function StatCard({
  label,
  value,
  sub,
  positive = true,
  isPercent = false,
  format = "currency",
  children,
}: {
  label: string;
  value: number;
  sub?: string;
  positive?: boolean;
  isPercent?: boolean;
  format?: "currency" | "number" | "percent";
  children?: ReactNode;
}) {
  const color = value < 0 ? "text-red-600" : positive ? "text-slate-900" : "text-slate-900";
  const formatted =
    format === "percent"
      ? `${value}%`
      : format === "number"
        ? value.toLocaleString()
        : formatCurrency(value);
  return (
    <Card>
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${color}`}>
        {formatted}
        {isPercent && <span className="ml-0.5 text-base font-medium text-slate-500">%</span>}
      </p>
      {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
      {children}
    </Card>
  );
}

export function Badge({ children, tone = "slate" }: { children: ReactNode; tone?: string }) {
  const tones: Record<string, string> = {
    slate: "bg-slate-100 text-slate-700",
    green: "bg-emerald-100 text-emerald-700",
    amber: "bg-amber-100 text-amber-700",
    red: "bg-red-100 text-red-700",
    blue: "bg-blue-100 text-blue-700",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}
