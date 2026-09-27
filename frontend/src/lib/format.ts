const DATE_TIME = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

/** Formats an ISO timestamp, or an em dash when the value is absent. */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return DATE_TIME.format(parsed);
}

/** Up to two initials from a person's name, for avatar fallbacks. */
export function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

/**
 * Formats a monetary string (as the API returns decimals) in the given currency.
 * Falls back to a plain fixed-point string if the currency code is not valid.
 */
export function formatMoney(
  value: string | number | null | undefined,
  currency = "USD",
): string {
  if (value === null || value === undefined || value === "") return "—";
  const amount = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(amount)) return "—";
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(amount);
  } catch {
    return amount.toFixed(2);
  }
}

/**
 * Formats a quantity, dropping the trailing zeros the API's fixed-scale decimals
 * carry, so `"79.000"` reads as `"79"` and `"45.500"` as `"45.5"`. Units are never
 * shown — they are a product attribute, not part of a stock figure.
 */
export function formatQuantity(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  let text = typeof value === "number" ? String(value) : value.trim();
  if (text.includes(".")) {
    text = text.replace(/0+$/, "").replace(/\.$/, "");
  }
  if (text === "" || text === "-") text = "0";
  return text;
}
