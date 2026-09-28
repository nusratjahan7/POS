import * as React from "react";

import { mediaUrl } from "@/lib/api/client";
import type { SaleReceipt } from "@/lib/api/sales";
import { formatDateTime, formatMoney, formatQuantity } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { InvoiceVariant } from "@/lib/invoice/styles";

function InvoiceLine({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className={strong ? "inv-line inv-line-strong" : "inv-line"}>
      <span>{label}</span>
      <span className="inv-num">{value}</span>
    </div>
  );
}

function InvoiceMeta({ label, value }: { label: string; value: string }) {
  return (
    <div className="inv-meta-row">
      <span className="inv-label">{label}</span>
      <span className="inv-value">{value}</span>
    </div>
  );
}

export type InvoiceDocumentProps = React.ComponentProps<"div"> & {
  receipt: SaleReceipt;
  /** `thermal` prints to 80mm paper; `a4` prints a full-page invoice. */
  variant: InvoiceVariant;
};

/**
 * The one invoice/receipt template.
 *
 * It renders the same markup for both layouts — the variant only changes the
 * stylesheet (see `invoiceCss`). The same component is shown in the on-screen
 * preview and its HTML is handed to the printer, so what the cashier sees is what
 * comes out of the printer.
 */
export function InvoiceDocument({ receipt, variant, className, ...props }: InvoiceDocumentProps) {
  const { business, branch, sale } = receipt;
  const currency = business.currency;
  const money = (value: string | number | null | undefined) => formatMoney(value, currency);
  const logo = mediaUrl(business.logo_url);

  // Prefer the branch's own address, falling back to the business's, without ever
  // printing the same line twice.
  const addresses = [branch.address, business.address].filter(
    (value, index, all): value is string => Boolean(value) && all.indexOf(value) === index,
  );
  const phone = branch.phone ?? business.phone;

  const hasDiscount = Number(sale.discount) > 0;
  const hasTax = Number(sale.tax) > 0;
  const hasChange = Number(sale.change_amount) > 0;
  const hasDue = Number(sale.due) > 0;

  return (
    <div className={cn("inv", variant === "a4" ? "inv-a4" : "inv-thermal", className)} {...props}>
      <header className="inv-head">
        <div className="inv-brand">
          {logo ? (
            // The logo must serialize into the standalone print document as a plain
            // absolute URL, so next/image (which rewrites src/srcset) is not used here.
            // eslint-disable-next-line @next/next/no-img-element
            <img className="inv-logo" src={logo} alt="" />
          ) : null}
          <div>
            <div className="inv-store">{business.name}</div>
            <div className="inv-branch">
              {branch.name}
              {branch.code ? ` · ${branch.code}` : ""}
            </div>
            {addresses.map((line) => (
              <div key={line} className="inv-contact">
                {line}
              </div>
            ))}
            {phone ? <div className="inv-contact">{phone}</div> : null}
            {business.email ? <div className="inv-contact">{business.email}</div> : null}
          </div>
        </div>
        <div className="inv-titles">
          <div className="inv-doc-title">{variant === "a4" ? "Invoice" : "Receipt"}</div>
          <div className="inv-doc-number">{sale.sale_number}</div>
          {sale.status === "voided" ? <div className="inv-doc-state">Voided</div> : null}
        </div>
      </header>

      <section className="inv-meta">
        <InvoiceMeta label="Date" value={formatDateTime(sale.sold_at)} />
        <InvoiceMeta label="Cashier" value={sale.cashier?.full_name ?? "—"} />
        <InvoiceMeta label="Customer" value={sale.customer?.name ?? "Walk-in"} />
      </section>

      <table className="inv-items">
        <thead>
          <tr>
            <th className="inv-col-no">#</th>
            <th>Item</th>
            <th className="inv-num">Qty</th>
            <th className="inv-num">Price</th>
            <th className="inv-num inv-disc-col">Disc</th>
            <th className="inv-num">Amount</th>
          </tr>
        </thead>
        <tbody>
          {sale.items.map((item, index) => (
            <tr key={item.id}>
              <td className="inv-col-no">{index + 1}</td>
              <td>
                <div className="inv-item-name">{item.product_name}</div>
                <div className="inv-item-sku">
                  {item.sku}
                  {item.unit ? ` · ${item.unit}` : ""}
                </div>
              </td>
              <td className="inv-num">{formatQuantity(item.quantity)}</td>
              <td className="inv-num">{money(item.unit_price)}</td>
              <td className="inv-num inv-disc-col">
                {Number(item.discount) > 0 ? `-${money(item.discount)}` : "—"}
              </td>
              <td className="inv-num">{money(item.line_total)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="inv-totals">
        <InvoiceLine label="Subtotal" value={money(sale.subtotal)} />
        {hasDiscount ? <InvoiceLine label="Discount" value={`-${money(sale.discount)}`} /> : null}
        {hasTax ? <InvoiceLine label={business.tax_label} value={money(sale.tax)} /> : null}
        <InvoiceLine label="Total" value={money(sale.total)} strong />
      </div>

      <section className="inv-payments">
        <div className="inv-section-title">Payment</div>
        {sale.payments.map((payment) => (
          <InvoiceLine
            key={payment.id}
            label={
              payment.reference
                ? `${payment.payment_method.name} · ${payment.reference}`
                : payment.payment_method.name
            }
            value={money(payment.amount)}
          />
        ))}
        <InvoiceLine label="Paid" value={money(sale.paid)} />
        {hasChange ? <InvoiceLine label="Change" value={money(sale.change_amount)} /> : null}
        {hasDue ? <InvoiceLine label="Due" value={money(sale.due)} strong /> : null}
      </section>

      <footer className="inv-foot">
        {sale.note ? (
          <div className="inv-note">
            <strong>Note:</strong> {sale.note}
          </div>
        ) : null}
        <div className="inv-thanks">Thank you for your business!</div>
        <div className="inv-fine">
          {sale.sale_number} · {business.name}
        </div>
      </footer>
    </div>
  );
}
