import ResourcePage, { money, dateOnly } from "../components/ResourcePage";

export default function SavingsGoalsPage() {
  return (
    <ResourcePage
      title="Savings Goals"
      description="Emergency fund, vacation, house down payment…"
      path="/savings-goals"
      fields={[
        { key: "name", label: "Goal", type: "text", required: true },
        { key: "target_amount", label: "Target Amount", type: "number", required: true, defaultValue: 0, render: money },
        { key: "current_amount", label: "Saved So Far", type: "number", defaultValue: 0, render: money },
        { key: "target_date", label: "Target Date", type: "date", render: dateOnly },
        { key: "notes", label: "Notes", type: "textarea", hideInTable: true },
      ]}
    />
  );
}
