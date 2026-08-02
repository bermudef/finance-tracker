import { useState } from "react";
import ResourcePage, { money } from "../components/ResourcePage";
import { downloadCsv } from "../api/client";

export default function BudgetsPage() {
  const [exporting, setExporting] = useState(false);

  async function handleExport() {
    setExporting(true);
    try {
      await downloadCsv("/budgets/export", "budgets.csv");
    } catch {
      alert("Export failed — try again.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <ResourcePage
      title="Budgets"
      description="Monthly spending limits per category — rollover carries unused amounts into next month"
      path="/budgets"
      fields={[
        { key: "name", label: "Name", type: "text", required: true },
        { key: "amount", label: "Monthly Amount", type: "number", required: true, defaultValue: 0, render: money },
        {
          key: "period",
          label: "Period",
          type: "select",
          required: true,
          options: [
            { value: "weekly", label: "Weekly" },
            { value: "monthly", label: "Monthly" },
            { value: "yearly", label: "Yearly" },
          ],
          defaultValue: "monthly",
        },
        { key: "rollover", label: "Rollover unused into next month", type: "checkbox", defaultValue: false },
        { key: "category_id", label: "Category ID", type: "number", hideInTable: true },
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
