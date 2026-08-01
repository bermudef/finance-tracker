export function formatCurrency(
  amount: number,
  currency = "USD",
  showSign = false
): string {
  const abs = Math.abs(amount);
  const formatted = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(abs);

  if (!showSign) return formatted;
  return amount < 0 ? `-${formatted}` : `+${formatted}`;
}

export function formatDate(iso: string): string {
  return new Date(iso + "T00:00:00").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
