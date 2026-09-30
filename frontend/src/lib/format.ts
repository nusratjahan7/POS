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
 *
 * A whole amount drops its zero cents (`2,550.00` → `2,550`) while real cents are
 * kept (`19.80`), so totals read like price tags rather than ledger entries.
 * Falls back to a plain fixed-point string if the currency code is not valid.
 */
export function formatMoney(
  value: string | number | null | undefined,
  currency = "USD",
): string {
  if (value === null || value === undefined || value === "") return "—";
  const amount = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(amount)) return "—";
  const rounded = Math.round(amount * 100) / 100;
  const digits = Number.isInteger(rounded) ? 0 : 2;
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(rounded);
  } catch {
    return rounded.toFixed(digits);
  }
}

/**
 * Formats a monetary value as a grouped plain number, with no currency attached.
 * Used where a document carries one currency throughout (receipts, invoices), so
 * restating the code on every line is noise. A zero cents part is dropped
 * (`2,550.00` → `2,550`) while real cents are kept (`19.80`).
 */
export function formatAmount(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const amount = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(amount)) return "—";
  return amount
    .toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    .replace(/\.00$/, "");
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
