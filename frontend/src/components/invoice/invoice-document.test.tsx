import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { InvoiceDocument } from "./invoice-document";
import type { SaleReceipt } from "@/lib/api/sales";
import { formatMoney, formatQuantity } from "@/lib/format";

const receipt: SaleReceipt = {
  business: {
    name: "Acme Mart",
    logo_url: "/media/logo.png",
    phone: "+1 555 0100",
    email: "hello@acme.test",
    address: "1 Market Street",
    currency: "USD",
    tax_label: "VAT",
  },
  branch: {
    id: "b1",
    name: "Downtown",
    code: "DT",
    address: "22 High Street",
    phone: "+1 555 0199",
  },
  sale: {
    id: "s1",
    sale_number: "INV-20260101-ABCDEF",
    branch: { id: "b1", name: "Downtown" },
    register_id: null,
    customer: { id: "c1", name: "Jane Doe", balance: "0.00" },
    cashier: { id: "u1", full_name: "Sam Cashier" },
    subtotal: "20.00",
    discount: "2.00",
    tax: "1.80",
    total: "19.80",
    paid: "19.80",
    due: "0.00",
    change_amount: "5.20",
    status: "completed",
    note: "Delivery",
    items: [
      {
        id: "i1",
        product_id: "p1",
        product_name: "Coffee Beans",
        sku: "BEAN-1",
        unit: "kg",
        quantity: "2.000",
        unit_price: "10.00",
        discount: "2.00",
        subtotal: "20.00",
        line_total: "18.00",
      },
    ],
    payments: [
      {
        id: "pay1",
        payment_method: { id: "m1", name: "Cash", code: "cash", kind: "cash" },
        amount: "19.80",
        tendered: "25.00",
        change_given: "5.20",
        reference: null,
        note: null,
        paid_at: "2026-01-01T10:30:00Z",
      },
    ],
    sold_at: "2026-01-01T10:30:00Z",
    created_at: "2026-01-01T10:30:00Z",
  },
};

afterEach(cleanup);

describe("InvoiceDocument", () => {
  it("carries the store, branch, invoice and cashier details", () => {
    render(<InvoiceDocument receipt={receipt} variant="a4" />);

    expect(screen.getByText("Acme Mart")).toBeTruthy();
    expect(screen.getByText("Downtown · DT")).toBeTruthy();
    expect(screen.getByText("INV-20260101-ABCDEF")).toBeTruthy();
    expect(screen.getByText("Sam Cashier")).toBeTruthy();
    expect(screen.getByText("Jane Doe")).toBeTruthy();
  });

  it("itemises each product with its quantity and line total", () => {
    render(<InvoiceDocument receipt={receipt} variant="a4" />);

    expect(screen.getByText("Coffee Beans")).toBeTruthy();
    expect(screen.getByText("BEAN-1 · kg")).toBeTruthy();
    expect(screen.getByText(formatQuantity("2.000"))).toBeTruthy();
    expect(screen.getByText(formatMoney("18.00", "USD"))).toBeTruthy();
  });

  it("shows the totals, the tax label and the change given", () => {
    render(<InvoiceDocument receipt={receipt} variant="thermal" />);

    expect(screen.getByText("Subtotal")).toBeTruthy();
    expect(screen.getByText(formatMoney("20.00", "USD"))).toBeTruthy();
    expect(screen.getByText("VAT")).toBeTruthy();
    expect(screen.getByText("Change")).toBeTruthy();
    expect(screen.getByText(formatMoney("5.20", "USD"))).toBeTruthy();
  });

  it("resolves the logo through the media URL helper", () => {
    const { container } = render(<InvoiceDocument receipt={receipt} variant="a4" />);

    expect(container.querySelector("img.inv-logo")?.getAttribute("src")).toContain(
      "/media/logo.png",
    );
  });

  it("leaves out rows that do not apply to a settled sale", () => {
    render(<InvoiceDocument receipt={receipt} variant="a4" />);

    expect(screen.queryByText("Due")).toBeNull();
    expect(screen.queryByText("Voided")).toBeNull();
  });
});
