import ResourcePage from "../components/ResourcePage";

export default function CategoriesPage() {
  return (
    <ResourcePage
      title="Categories"
      description="Income and expense categories"
      path="/categories"
      fields={[
        { key: "name", label: "Name", type: "text", required: true },
        {
          key: "type",
          label: "Type",
          type: "select",
          required: true,
          options: [
            { value: "expense", label: "Expense" },
            { value: "income", label: "Income" },
          ],
          defaultValue: "expense",
        },
        { key: "color", label: "Color (hex)", type: "text", placeholder: "#10b981", hideInTable: true },
      ]}
    />
  );
}
