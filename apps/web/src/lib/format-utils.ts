export function normalizeDateKey(value: string | null | undefined): string {
  if (!value) return "";
  return value.length >= 10 ? value.slice(0, 10) : value;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
