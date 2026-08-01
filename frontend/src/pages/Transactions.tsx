import { useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  exportTransactionsCsv,
  importTransactionsCsv,
  type Account,
  type Category,
  type Transaction,
} from "../api/client";
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
  const [importing, setImporting] = useState(false);
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = () =>
    api
      .get<Transaction[]>("/transactions")
      .then(setTransactions)
      .catch((err) => console.error(err));

  useEffect(() => {
    Promise.all([
      load(),
      api.get<Account[]>("/accounts").then(setAccounts),
      api.get<Category[]>("/categories").then(setCategories),
    ]).finally(() => setLoading(false));
  }, []);

  const handleExport = async () => {
    try {
      const blob = await exportTransactionsCsv();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `transactions-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      setImportMessage("Export failed — see console.");
    }
  };

  const handleImportFile = async (file: File) => {
    setImporting(true);
    setImportMessage(null);
    try {
      const result = await importTransactionsCsv(file);
      setImportMessage(
        `Imported ${result.created} transaction${result.created === 1 ? "" : "s"}${
          result.skipped
            ? `, skipped ${result.skipped} row${result.skipped === 1 ? "" : "s"}: ${result.errors
                .map((e) => `row ${e.row} (${e.error})`)
                .join("; ")}`
            : ""
        }.`
      );
      await load();
    } catch (err) {
      setImportMessage(err instanceof Error ? err.message : "Import failed.");
    } finally {
      setImporting(false);
    }
  };

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
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Transactions</h1>
          <p className="text-sm text-slate-500">Search, filter, and review your activity</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleImportFile(f);
              e.target.value = ""; // allow re-selecting the same file
            }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {importing ? "Importing…" : "Import CSV"}
          </button>
          <button
            onClick={handleExport}
            className="rounded-lg border border-emerald-600 bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700"
          >
            Export CSV
          </button>
        </div>
      </header>

      {importMessage && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {importMessage}
        </div>
      )}

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
