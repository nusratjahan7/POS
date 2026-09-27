import type { SaleReceipt } from "@/lib/api/sales";
import { formatDateTime, formatMoney } from "@/lib/format";

/** Escape anything that came from the database before it goes into receipt HTML. */
function escapeHtml(value: string): string {
  return value.replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] ?? char,
  );
}

function row(label: string, value: string, strong = false): string {
  return `<div class="row${strong ? " strong" : ""}"><span>${escapeHtml(label)}</span><span>${escapeHtml(value)}</span></div>`;
}

/**
 * Print a receipt through the browser.
 *
 * Built as a standalone document in its own window so the app needs no print
 * stylesheet and nothing about the till's layout leaks onto the paper. Returns
 * false when the browser blocks the window.
 */
export function printReceipt({ business, sale }: SaleReceipt): boolean {
  const currency = business.currency;
  const money = (value: string | number | null) => formatMoney(value, currency);

  const items = sale.items
    .map(
      (item) => `<tr>
        <td>${escapeHtml(item.product_name)}<span class="muted"> · ${escapeHtml(item.sku)}</span></td>
        <td class="right">${escapeHtml(item.quantity)}</td>
        <td class="right">${escapeHtml(money(item.unit_price))}</td>
        <td class="right">${escapeHtml(money(item.line_total))}</td>
      </tr>`,
    )
    .join("");

  const payments = sale.payments
    .map((payment) =>
      row(
        payment.reference
          ? `${payment.payment_method.name} (${payment.reference})`
          : payment.payment_method.name,
        money(payment.amount),
      ),
    )
    .join("");

  const contact = [business.address, business.phone, business.email]
    .filter((value): value is string => Boolean(value))
    .map((value) => `<div>${escapeHtml(value)}</div>`)
    .join("");

  const html = `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>${escapeHtml(sale.sale_number)}</title>
    <style>
      * { box-sizing: border-box; }
      body { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 12px; margin: 0; padding: 16px; color: #111; }
      h1 { font-size: 15px; margin: 0 0 2px; text-align: center; }
      .muted { color: #666; }
      .center { text-align: center; }
      .head { margin-bottom: 12px; }
      .sep { border-top: 1px dashed #999; margin: 10px 0; }
      table { width: 100%; border-collapse: collapse; }
      th { text-align: left; font-weight: 600; border-bottom: 1px solid #999; padding-bottom: 3px; }
      td { padding: 3px 0; vertical-align: top; }
      .right { text-align: right; white-space: nowrap; }
      .row { display: flex; justify-content: space-between; gap: 12px; padding: 2px 0; }
      .strong { font-weight: 700; font-size: 14px; border-top: 1px solid #999; margin-top: 4px; padding-top: 6px; }
      .invoice { text-align: center; margin-top: 10px; }
    </style>
  </head>
  <body>
    <div class="head center">
      <h1>${escapeHtml(business.name)}</h1>
      ${contact}
    </div>
    <div class="sep"></div>
    ${row("Invoice", sale.sale_number)}
    ${row("Date", formatDateTime(sale.sold_at))}
    ${row("Branch", sale.branch.name)}
    ${row("Cashier", sale.cashier?.full_name ?? "—")}
    ${row("Customer", sale.customer?.name ?? "Walk-in")}
    <div class="sep"></div>
    <table>
      <thead>
        <tr>
          <th>Item</th>
          <th class="right">Qty</th>
          <th class="right">Price</th>
          <th class="right">Amount</th>
        </tr>
      </thead>
      <tbody>${items}</tbody>
    </table>
    <div class="sep"></div>
    ${row("Subtotal", money(sale.subtotal))}
    ${sale.discount !== "0.00" ? row("Discount", `-${money(sale.discount)}`) : ""}
    ${sale.tax !== "0.00" ? row(business.tax_label, money(sale.tax)) : ""}
    ${row("Total", money(sale.total), true)}
    <div class="sep"></div>
    ${payments}
    ${row("Paid", money(sale.paid))}
    ${sale.change_amount !== "0.00" ? row("Change", money(sale.change_amount), true) : ""}
    ${sale.due !== "0.00" ? row("Due", money(sale.due), true) : ""}
    <div class="invoice">Thank you!</div>
  </body>
</html>`;

  const printWindow = window.open("", "_blank", "width=420,height=640");
  if (!printWindow) return false;

  printWindow.document.write(html);
  printWindow.document.close();
  printWindow.focus();
  printWindow.print();
  return true;
}
