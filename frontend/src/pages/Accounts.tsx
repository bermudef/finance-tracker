import ResourcePage, { money } from "../components/ResourcePage";

const ACCOUNT_TYPES = [
  { value: "checking", label: "Checking" },
  { value: "savings", label: "Savings" },
  { value: "high-yield savings", label: "High Yield Savings" },
  { value: "cash", label: "Cash" },
];

export default function AccountsPage() {
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
    />
  );
}
