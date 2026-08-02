import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  api,
  recurringApi,
  type Account,
  type Category,
  type RecurringTransactionItem,
} from "../api/client";
import { Badge, Card } from "../components/ui";
import { formatCurrency } from "../lib/format";

const FREQUENCIES = [
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "yearly", label: "Yearly" },
];

const emptyForm = {
  name: "",
  account_id: "",
  category_id: "",
  amount: "",
  frequency: "monthly",
  next_date: new Date().toISOString().slice(0, 10),
};

export default function RecurringPage() {
  const [items, setItems] = useState<RecurringTransactionItem[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [processMessage, setProcessMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [items, accounts, categories] = await Promise.all([
        recurringApi.list(),
        api.get<Account[]>("/accounts"),
        api.get<Category[]>("/categories"),
      ]);
      setItems(items);
      setAccounts(accounts.filter((a) => a.is_active));
      setCategories(categories.filter((c) => c.type === "expense"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await recurringApi.create({
        name: form.name,
        account_id: Number(form.account_id),
        category_id: form.category_id ? Number(form.category_id) : null,
        amount: Number(form.amount),
        frequency: form.frequency,
        next_date: form.next_date,
      });
      setForm(emptyForm);
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleActive(item: RecurringTransactionItem) {
    try {
      await recurringApi.update(item.id, { is_active: !item.is_active });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update");
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this recurring item?")) return;
    try {
      await recurringApi.remove(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    }
  }

  async function handleProcess() {
    setProcessing(true);
    setProcessMessage(null);
    try {
      const result = await recurringApi.process();
      setProcessMessage(result.message);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to process");
    } finally {
      setProcessing(false);
    }
  }

  const accountName = (id: number) => accounts.find((a) => a.id === id)?.name ?? `#${id}`;

  return (
    <div className="space-y-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Recurring Transactions</h1>
          <p className="text-sm text-slate-500">
            Rent, subscriptions, and paychecks — due items auto-post to Transactions
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button
            onClick={handleProcess}
            disabled={processing}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {processing ? "Processing…" : "Process now"}
          </button>
          <button
            onClick={() => setShowForm((s) => !s)}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
          >
            {showForm ? "Cancel" : "+ Add Recurring"}
          </button>
        </div>
      </header>

      {processMessage && (
        <p className="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{processMessage}</p>
      )}
      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      {showForm && (
        <Card>
          <form onSubmit={handleCreate} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="recur-name">
                Name
              </label>
              <input
                id="recur-name"
                required
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="Rent"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="recur-account">
                Account
              </label>
              <select
                id="recur-account"
                required
                value={form.account_id}
                onChange={(e) => setForm((f) => ({ ...f, account_id: e.target.value }))}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
              >
                <option value="">Select…</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="recur-amount">
                Amount (negative = expense)
              </label>
              <input
                id="recur-amount"
                type="number"
                step="0.01"
                required
                value={form.amount}
                onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="recur-frequency">
                Frequency
              </label>
              <select
                id="recur-frequency"
                value={form.frequency}
                onChange={(e) => setForm((f) => ({ ...f, frequency: e.target.value }))}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
              >
                {FREQUENCIES.map((f) => (
                  <option key={f.value} value={f.value}>{f.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="recur-date">
                Next occurrence
              </label>
              <input
                id="recur-date"
                type="date"
                required
                value={form.next_date}
                onChange={(e) => setForm((f) => ({ ...f, next_date: e.target.value }))}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="recur-category">
                Category
              </label>
              <select
                id="recur-category"
                value={form.category_id}
                onChange={(e) => setForm((f) => ({ ...f, category_id: e.target.value }))}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
              >
                <option value="">None</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div className="sm:col-span-2 lg:col-span-3">
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
                <th className="px-5 py-3 font-medium">Name</th>
                <th className="px-5 py-3 font-medium">Amount</th>
                <th className="px-5 py-3 font-medium">Frequency</th>
                <th className="px-5 py-3 font-medium">Account</th>
                <th className="px-5 py-3 font-medium">Next occurrence</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50">
                  <td className="px-5 py-3 font-medium text-slate-800">{item.name}</td>
                  <td className={`px-5 py-3 tabular-nums ${item.amount < 0 ? "text-slate-700" : "text-emerald-600"}`}>
                    {formatCurrency(item.amount)}
                  </td>
                  <td className="px-5 py-3 capitalize text-slate-600">{item.frequency}</td>
                  <td className="px-5 py-3 text-slate-600">{accountName(item.account_id)}</td>
                  <td className="px-5 py-3 tabular-nums text-slate-600">{item.next_date}</td>
                  <td className="px-5 py-3">
                    {item.is_active ? <Badge tone="green">Active</Badge> : <Badge>Paused</Badge>}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <button
                      onClick={() => handleToggleActive(item)}
                      className="rounded px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
                    >
                      {item.is_active ? "Pause" : "Resume"}
                    </button>
                    <button
                      onClick={() => handleDelete(item.id)}
                      className="rounded px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-5 py-8 text-center text-slate-400">
                    No recurring items yet. Add rent, subscriptions, or a paycheck above.
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
