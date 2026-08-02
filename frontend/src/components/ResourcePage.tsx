import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { api } from "../api/client";
import { Badge, Card } from "./ui";
import { formatCurrency } from "../lib/format";

export type FieldType =
  | "text"
  | "number"
  | "date"
  | "select"
  | "checkbox"
  | "textarea";

export interface FieldConfig {
  key: string;
  label: string;
  type: FieldType;
  required?: boolean;
  options?: Array<{ value: string; label: string }>;
  placeholder?: string;
  /** Format a raw value into display text (e.g. currency). */
  render?: (value: unknown, row: Record<string, unknown>) => ReactNode;
  hideInTable?: boolean;
  defaultValue?: unknown;
}

interface ResourcePageProps {
  title: string;
  description?: string;
  path: string;
  fields: FieldConfig[];
  /** Extra buttons rendered in the page header (e.g. CSV export). */
  headerActions?: ReactNode;
  onCreated?: () => void;
}

function toDisplayValue(field: FieldConfig, value: unknown): unknown {
  if (value === null || value === undefined) return "";
  if (field.type === "checkbox") return Boolean(value);
  return value;
}

export default function ResourcePage({
  title,
  description,
  path,
  fields,
  headerActions,
  onCreated,
}: ResourcePageProps) {
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const emptyForm = () =>
    Object.fromEntries(fields.map((f) => [f.key, f.defaultValue ?? (f.type === "checkbox" ? false : "")]));

  const [form, setForm] = useState<Record<string, unknown>>(emptyForm);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await api.get<Array<Record<string, unknown>>>(path));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    load();
  }, [load]);

  function setField(key: string, value: unknown) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const payload = { ...form };
    for (const f of fields) {
      const v = payload[f.key];
      if (f.type === "number") {
        payload[f.key] = v === "" ? undefined : Number(v);
      } else if (f.type === "checkbox") {
        payload[f.key] = Boolean(v);
      } else if (v === "") {
        payload[f.key] = null;
      }
    }
    try {
      await api.post(path, payload);
      setForm(emptyForm());
      setShowForm(false);
      await load();
      onCreated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this item?")) return;
    try {
      await api.delete(`${path}/${id}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    }
  }

  const tableFields = fields.filter((f) => !f.hideInTable);

  return (
    <div className="space-y-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
          {description && <p className="text-sm text-slate-500">{description}</p>}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {headerActions}
          <button
            onClick={() => setShowForm((s) => !s)}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
          >
            {showForm ? "Cancel" : `+ Add ${title.replace(/s$/, "")}`}
          </button>
        </div>
      </header>

      {showForm && (
        <Card>
          <form onSubmit={handleCreate} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {fields.map((f) => (
              <div key={f.key} className={f.type === "textarea" ? "sm:col-span-2 lg:col-span-3" : ""}>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor={`field-${f.key}`}>
                  {f.label}
                </label>
                {f.type === "select" ? (
                  <select
                    id={`field-${f.key}`}
                    required={f.required}
                    value={String(form[f.key] ?? "")}
                    onChange={(e) => setField(f.key, e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                  >
                    {f.options?.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                ) : f.type === "checkbox" ? (
                  <input
                    id={`field-${f.key}`}
                    type="checkbox"
                    checked={Boolean(form[f.key])}
                    onChange={(e) => setField(f.key, e.target.checked)}
                    className="mt-2 h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                  />
                ) : (
                  <input
                    id={`field-${f.key}`}
                    type={f.type}
                    required={f.required}
                    placeholder={f.placeholder}
                    value={String(form[f.key] ?? "")}
                    onChange={(e) => setField(f.key, e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  />
                )}
              </div>
            ))}
            <div className="sm:col-span-2 lg:col-span-3">
              {error && (
                <p className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
              )}
              <button
                type="submit"
                disabled={submitting}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                {submitting ? "Saving…" : "Save"}
              </button>
            </div>
          </form>
        </Card>
      )}

      <Card className="overflow-x-auto p-0">
        {loading ? (
          <p className="p-6 text-sm text-slate-500">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-400">
                {tableFields.map((f) => (
                  <th key={f.key} className="px-5 py-3 font-medium">{f.label}</th>
                ))}
                <th className="px-5 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((row) => (
                <tr key={row.id as number} className="hover:bg-slate-50">
                  {tableFields.map((f) => (
                    <td key={f.key} className="px-5 py-3 text-slate-700">
                      {f.render
                        ? f.render(row[f.key], row)
                        : f.type === "checkbox"
                          ? (row[f.key] ? <Badge tone="green">Yes</Badge> : <Badge>No</Badge>)
                          : String(toDisplayValue(f, row[f.key]))}
                    </td>
                  ))}
                  <td className="px-5 py-3 text-right">
                    <button
                      onClick={() => handleDelete(row.id as number)}
                      className="rounded px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={tableFields.length + 1} className="px-5 py-8 text-center text-slate-400">
                    Nothing here yet. Add your first item above.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

export const money = (v: unknown) => formatCurrency(Number(v ?? 0));
export const pct = (v: unknown) => `${Number(v ?? 0)}%`;
export const dateOnly = (v: unknown) =>
  typeof v === "string" && v ? new Date(v + "T00:00:00").toLocaleDateString("en-US") : "—";
