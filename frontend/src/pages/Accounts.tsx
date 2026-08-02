import { useState } from "react";
import ResourcePage, { money } from "../components/ResourcePage";
import { downloadCsv } from "../api/client";

const ACCOUNT_TYPES = [
  { value: "checking", label: "Checking" },
  { value: "savings", label: "Savings" },
  { value: "high-yield savings", label: "High Yield Savings" },
  { value: "cash", label: "Cash" },
];

export default function AccountsPage() {
  const [exporting, setExporting] = useState(false);

  async function handleExport() {
    setExporting(true);
    try {
      await downloadCsv("/accounts/export", "accounts.csv");
    } catch {
      alert("Export failed — try again.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <ResourcePage
      title="Accounts"
      description="Bank and cash accounts"
      path="/accounts"
      fields={[
        { key: "name", label: "Name", type: "text", required: true },
        { key: "type", label: "Type", type: "select", required: true, options: ACCOUNT_TYPES, defaultValue: "checking" },
        { key: "opening_balance", label: "Opening Balance", type: "number", defaultValue: 0, render: money },
        { key: "is_active", label: "Active", type: "checkbox", defaultValue: true, hideInTable: true },
      ]}
      headerActions={
        <button
          onClick={handleExport}
          disabled={exporting}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {exporting ? "Exporting…" : "Export CSV"}
        </button>
      }
    />
  );
}
