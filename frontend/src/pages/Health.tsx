import { useEffect, useState } from "react";
import { PolarAngleAxis, RadialBar, RadialBarChart, ResponsiveContainer } from "recharts";
import { api, type HealthScore } from "../api/client";
import { Badge, Card } from "../components/ui";

const GRADE_COLORS: Record<HealthScore["grade"], string> = {
  Excellent: "#10b981",
  Good: "#0ea5e9",
  Fair: "#f59e0b",
  "Needs work": "#ef4444",
};

const SCORE_COLORS: Record<string, string> = {
  savings_rate: "bg-emerald-500",
  emergency_fund: "bg-sky-500",
  debt_burden: "bg-violet-500",
  budget_adherence: "bg-amber-500",
  credit_utilization: "bg-rose-500",
  savings_goals: "bg-teal-500",
};

const STATUS_LABEL: Record<HealthScore["subscores"][number]["status"], string> = {
  on_track: "On track",
  at_risk: "At risk",
  over: "Over",
};

export default function HealthPage() {
  const [data, setData] = useState<HealthScore | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<HealthScore>("/health-score")
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-slate-500">Loading health score…</p>;
  if (error) return <p className="text-sm text-red-600">Failed to load: {error}</p>;
  if (!data) return null;

  const color = GRADE_COLORS[data.grade];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Financial Health</h1>
        <p className="text-sm text-slate-500">
          Your overall score for {data.period_label} — updated {data.as_of}
        </p>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="flex flex-col items-center justify-center py-6">
          <div className="relative h-56 w-56">
            <ResponsiveContainer width="100%" height="100%">
              <RadialBarChart
                innerRadius="78%"
                outerRadius="100%"
                data={[{ value: data.score }]}
                startAngle={90}
                endAngle={-270}
              >
                <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                <RadialBar
                  dataKey="value"
                  cornerRadius={14}
                  fill={color}
                  background={{ fill: "#e2e8f0" }}
                />
              </RadialBarChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <p className="text-5xl font-bold tabular-nums text-slate-900">{data.score}</p>
              <p className="mt-1 text-sm font-medium text-slate-500">out of 100</p>
            </div>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <Badge tone={data.score >= 80 ? "green" : data.score >= 60 ? "blue" : data.score >= 40 ? "amber" : "red"}>
              {data.grade}
            </Badge>
            <span className="text-xs text-slate-400">
              {data.score >= 80
                ? "Your finances are in great shape"
                : data.score >= 60
                  ? "Solid, with room to improve"
                  : data.score >= 40
                    ? "A few areas need attention"
                    : "Priority fixes needed"}
            </span>
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <h2 className="mb-4 text-base font-semibold text-slate-900">What drives your score</h2>
          <ul className="space-y-4">
            {data.subscores.map((s) => (
              <li key={s.key}>
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className={`h-2.5 w-2.5 rounded-full ${SCORE_COLORS[s.key] ?? "bg-slate-400"}`} />
                    <p className="text-sm font-medium text-slate-800">{s.label}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                      {s.weight}%
                    </span>
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                        s.status === "on_track"
                          ? "bg-emerald-100 text-emerald-700"
                          : s.status === "at_risk"
                            ? "bg-amber-100 text-amber-700"
                            : "bg-red-100 text-red-700"
                      }`}
                    >
                      {STATUS_LABEL[s.status]}
                    </span>
                    <span className="w-10 text-right text-sm font-semibold tabular-nums text-slate-900">
                      {s.score}
                    </span>
                  </div>
                </div>
                <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full transition-all ${SCORE_COLORS[s.key] ?? "bg-emerald-500"}`}
                    style={{ width: `${Math.min(s.score, 100)}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-slate-500">{s.detail}</p>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card>
        <h2 className="mb-3 text-base font-semibold text-slate-900">Recommendations</h2>
        {data.recommendations.length === 0 ? (
          <p className="text-sm text-slate-500">
            Nothing to fix right now — keep up the good habits.
          </p>
        ) : (
          <ul className="space-y-2">
            {data.recommendations.map((r) => (
              <li key={r.key} className="flex items-start gap-3 rounded-lg border border-slate-100 bg-slate-50/50 px-4 py-3">
                <span className="mt-0.5 text-amber-500">●</span>
                <p className="text-sm text-slate-700">{r.text}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
