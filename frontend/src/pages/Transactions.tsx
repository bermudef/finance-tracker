import { useEffect, useMemo, useState } from "react";
import { api, type Account, type Category, type Transaction } from "../api/client";
import { Badge, Card } from "../components/ui";
import { formatCurrency, formatDate } from "../lib/format";

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [accountFilter, setAccountFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get<Transaction[]>("/transactions"),
      api.get<Account[]>("/accounts"),
      api.get<Category[]>("/categories"),
    ])
      .then(([txs, accs, cats]) => {
        setTransactions(txs);
        setAccounts(accs);
        setCategories(cats);
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    return transactions.filter((t) => {
      if (accountFilter && t.account_id !== Number(accountFilter)) return false;
      if (categoryFilter && t.category_id !== Number(categoryFilter)) return false;
      if (search) {
        const q = search.toLowerCase();
        const haystack = `${t.description ?? ""} ${t.merchant ?? ""} ${t.category_name ?? ""}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
  }, [transactions, accountFilter, categoryFilter, search]);

  if (loading) return <p className="text-sm text-slate-500">Loading transactions…</p>;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Transactions</h1>
        <p className="text-sm text-slate-500">Search, filter, and review your activity</p>
      </header>

      <Card className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          type="search"
          placeholder="Search description, merchant, category…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
        />
        <select
          value={accountFilter}
          onChange={(e) => setAccountFilter(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">All accounts</option>
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </Card>

      <Card className="overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-400">
              <th className="px-5 py-3 font-medium">Date</th>
              <th className="px-5 py-3 font-medium">Description</th>
              <th className="px-5 py-3 font-medium">Account</th>
              <th className="px-5 py-3 font-medium">Category</th>
              <th className="px-5 py-3 text-right font-medium">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.map((t) => (
              <tr key={t.id} className="hover:bg-slate-50">
                <td className="whitespace-nowrap px-5 py-3 text-slate-600">{formatDate(t.date)}</td>
                <td className="px-5 py-3 font-medium text-slate-800">
                  {t.description || t.merchant || "—"}
                </td>
                <td className="px-5 py-3 text-slate-600">{t.account_name}</td>
                <td className="px-5 py-3">
                  {t.category_name ? <Badge>{t.category_name}</Badge> : <span className="text-slate-300">—</span>}
                </td>
                <td
                  className={`px-5 py-3 text-right font-semibold tabular-nums ${
                    t.amount < 0 ? "text-red-600" : "text-emerald-600"
                  }`}
                >
                  {formatCurrency(t.amount)}
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={5} className="px-5 py-8 text-center text-slate-400">
                  No transactions match your filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
