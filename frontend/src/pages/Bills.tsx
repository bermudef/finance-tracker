import ResourcePage, { money, dateOnly } from "../components/ResourcePage";

const FREQUENCIES = [
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "yearly", label: "Yearly" },
];

export default function BillsPage() {
  return (
    <ResourcePage
      title="Bills"
      description="Recurring bills and subscriptions"
      path="/bills"
      fields={[
        { key: "name", label: "Name", type: "text", required: true },
        { key: "amount", label: "Amount", type: "number", required: true, defaultValue: 0, render: money },
        { key: "due_date", label: "Due Date", type: "date", required: true, render: dateOnly },
        { key: "frequency", label: "Frequency", type: "select", required: true, options: FREQUENCIES, defaultValue: "monthly" },
        { key: "auto_pay", label: "Auto-Pay", type: "checkbox", defaultValue: false },
        { key: "notes", label: "Notes", type: "textarea", hideInTable: true },
      ]}
    />
  );
}
