import ResourcePage, { money, pct, dateOnly } from "../components/ResourcePage";

const DEBT_TYPES = [
  { value: "mortgage", label: "Mortgage" },
  { value: "auto", label: "Auto Loan" },
  { value: "student", label: "Student Loan" },
  { value: "personal", label: "Personal Loan" },
  { value: "credit_card", label: "Credit Card" },
  { value: "other", label: "Other" },
];

export default function DebtsPage() {
  return (
    <ResourcePage
      title="Debts"
      description="Mortgages, loans, and other obligations"
      path="/debts"
      fields={[
        { key: "name", label: "Name", type: "text", required: true },
        { key: "type", label: "Type", type: "select", required: true, options: DEBT_TYPES, defaultValue: "other" },
        { key: "principal", label: "Principal", type: "number", required: true, defaultValue: 0, render: money },
        { key: "interest_rate", label: "Interest Rate (%)", type: "number", defaultValue: 0, render: pct },
        { key: "min_payment", label: "Min Payment", type: "number", render: money },
        { key: "payment_due_date", label: "Payment Due Date", type: "date", render: dateOnly },
        { key: "remaining_term_months", label: "Term (months)", type: "number", hideInTable: true },
      ]}
    />
  );
}
