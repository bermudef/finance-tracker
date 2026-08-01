import ResourcePage, { money } from "../components/ResourcePage";

export default function BudgetsPage() {
  return (
    <ResourcePage
      title="Budgets"
      description="Monthly spending limits per category"
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
        { key: "category_id", label: "Category ID", type: "number", hideInTable: true },
      ]}
    />
  );
}
