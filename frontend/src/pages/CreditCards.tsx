import ResourcePage, { money, pct, dateOnly } from "../components/ResourcePage";

export default function CreditCardsPage() {
  return (
    <ResourcePage
      title="Credit Cards"
      description="Balances, limits, and APRs"
      path="/credit-cards"
      fields={[
        { key: "name", label: "Card Name", type: "text", required: true },
        { key: "balance", label: "Current Balance", type: "number", defaultValue: 0, render: money },
        { key: "credit_limit", label: "Credit Limit", type: "number", defaultValue: 0, render: money },
        { key: "apr", label: "APR (%)", type: "number", defaultValue: 0, render: pct },
        { key: "payment_due_date", label: "Payment Due Date", type: "date", render: dateOnly },
        { key: "min_payment", label: "Min Payment", type: "number", render: money },
      ]}
    />
  );
}
