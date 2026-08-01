import ResourcePage, { money } from "../components/ResourcePage";

const INVESTMENT_TYPES = [
  { value: "stock", label: "Stock" },
  { value: "etf", label: "ETF" },
  { value: "retirement", label: "Retirement" },
  { value: "crypto", label: "Crypto" },
  { value: "cash", label: "Cash" },
  { value: "other", label: "Other" },
];

export default function InvestmentsPage() {
  return (
    <ResourcePage
      title="Investments"
      description="Stocks, ETFs, and retirement accounts"
      path="/investments"
      fields={[
        { key: "name", label: "Name", type: "text", required: true },
        { key: "type", label: "Type", type: "select", required: true, options: INVESTMENT_TYPES, defaultValue: "other" },
        { key: "symbol", label: "Symbol", type: "text", placeholder: "VTI" },
        { key: "cost_basis", label: "Cost Basis", type: "number", defaultValue: 0, render: money },
        { key: "current_value", label: "Current Value", type: "number", defaultValue: 0, render: money },
        { key: "account_name", label: "Account", type: "text", placeholder: "Fidelity 401k" },
        { key: "notes", label: "Notes", type: "textarea", hideInTable: true },
      ]}
    />
  );
}
