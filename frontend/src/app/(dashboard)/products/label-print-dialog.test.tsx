import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { LabelPrintDialog } from "./label-print-dialog";

const { list } = vi.hoisted(() => ({ list: vi.fn() }));

vi.mock("@/lib/api/products", () => ({ productsApi: { list } }));

const product = {
  id: "p1",
  name: "Espresso Beans",
  slug: "espresso-beans",
  sku: "BEAN-1",
  barcode: "4006381333931",
  category_id: null,
  brand_id: null,
  category: null,
  brand: null,
  purchase_price: "1.00",
  selling_price: "12.99",
  discount_price: null,
  unit: "unit",
  minimum_stock: "0",
  stock_quantity: "10",
  description: null,
  image_url: null,
  is_active: true,
  stock_status: "in_stock",
  is_low_stock: false,
  created_at: "2026-10-10T09:00:00Z",
  updated_at: "2026-10-10T09:00:00Z",
} as never;

function renderDialog() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <LabelPrintDialog preselected={[product]} currency="USD" onClose={() => {}} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  list.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20, pages: 0 });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("LabelPrintDialog", () => {
  it("previews a thermal label for the preselected product", async () => {
    renderDialog();

    expect(await screen.findByText("Espresso Beans")).toBeTruthy();
    expect(screen.getByText(/1 label/)).toBeTruthy();
    expect(document.querySelector('.lbl-sheet[data-layout="thermal"]')).toBeTruthy();
  });

  it("repeats the run by the copy count", async () => {
    const user = userEvent.setup();
    renderDialog();

    const input = screen.getByLabelText("Copies per product");
    await user.clear(input);
    await user.type(input, "3");

    expect(await screen.findByText(/3 labels/)).toBeTruthy();
  });

  it("switches the sheet to the A4 layout", async () => {
    const user = userEvent.setup();
    renderDialog();

    await user.click(screen.getByRole("tab", { name: /A4 sheet/ }));

    await waitFor(() =>
      expect(document.querySelector('.lbl-sheet[data-layout="a4"]')).toBeTruthy(),
    );
  });
});
