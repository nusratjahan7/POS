"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { FileText, Printer, Search, Tag } from "lucide-react";

import { LabelSheet } from "@/components/labels/label-sheet";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { productsApi, type Product } from "@/lib/api/products";
import { formatMoney } from "@/lib/format";
import { printLabels } from "@/lib/labels/print";
import { buildLabelRun } from "@/lib/labels/run";
import { labelCss, type LabelData, type LabelLayout } from "@/lib/labels/styles";

/** A run this size is plenty for a shop-floor batch and keeps the preview light. */
const MAX_LABELS = 240;

/** Inject the label stylesheet for the live preview (no `@page`). */
function useLabelStyles(layout: LabelLayout) {
  React.useEffect(() => {
    const element = document.createElement("style");
    element.dataset.labelStyles = layout;
    element.textContent = labelCss(layout, { print: false });
    document.head.appendChild(element);
    return () => {
      element.remove();
    };
  }, [layout]);
}

/**
 * Preview and print barcode labels.
 *
 * Opened from a product row (one preselected) or from the list's "Print labels"
 * button (empty, with a searchable picker). The previewed sheet is exactly what is
 * sent to the printer.
 */
export function LabelPrintDialog({
  preselected,
  currency,
  onClose,
}: {
  preselected: Product[];
  currency: string;
  onClose: () => void;
}) {
  const [selected, setSelected] = React.useState<Product[]>(preselected);
  const [layout, setLayout] = React.useState<LabelLayout>("thermal");
  const [includePrice, setIncludePrice] = React.useState(true);
  const [copies, setCopies] = React.useState("1");
  const [search, setSearch] = React.useState("");
  const [query, setQuery] = React.useState("");

  const previewRef = React.useRef<HTMLDivElement>(null);
  useLabelStyles(layout);

  React.useEffect(() => {
    const timer = setTimeout(() => setQuery(search), 250);
    return () => clearTimeout(timer);
  }, [search]);

  const productsQuery = useQuery({
    queryKey: ["products", "label-picker", query],
    queryFn: () => productsApi.list({ search: query || undefined, page_size: 20 }),
  });
  const options = productsQuery.data?.items ?? [];

  const copiesNumber = Math.max(1, Math.floor(Number(copies) || 1));

  const seeds: LabelData[] = selected.map((product) => ({
    name: product.name,
    // A product with no barcode still labels — its SKU is the scannable code.
    code: product.barcode?.trim() ? product.barcode : product.sku,
    sku: product.sku,
    price: includePrice
      ? formatMoney(product.discount_price ?? product.selling_price, currency)
      : null,
  }));

  const fullRun = React.useMemo(() => buildLabelRun(seeds, copiesNumber), [seeds, copiesNumber]);
  const run = fullRun.slice(0, MAX_LABELS);

  function toggle(product: Product) {
    setSelected((current) =>
      current.some((item) => item.id === product.id)
        ? current.filter((item) => item.id !== product.id)
        : [...current, product],
    );
  }

  function handlePrint() {
    const node = previewRef.current;
    if (!node || run.length === 0) return;
    printLabels(node.outerHTML, layout);
  }

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>Print barcode labels</DialogTitle>
          <DialogDescription>
            Pick products and a label stock, then print. Each label carries the product&rsquo;s
            barcode — its SKU when it has none.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
          <div className="flex flex-col gap-3">
            <div className="relative">
              <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search products"
                aria-label="Search products to label"
                className="pl-8"
              />
            </div>

            <div className="max-h-64 overflow-y-auto rounded-md border">
              {productsQuery.isPending ? (
                <div className="flex flex-col gap-2 p-3">
                  {Array.from({ length: 4 }).map((_, index) => (
                    <Skeleton key={index} className="h-9 w-full" />
                  ))}
                </div>
              ) : options.length === 0 ? (
                <p className="text-muted-foreground p-4 text-center text-sm">No products found.</p>
              ) : (
                <ul className="divide-y">
                  {options.map((product) => {
                    const checked = selected.some((item) => item.id === product.id);
                    return (
                      <li key={product.id}>
                        <label className="flex cursor-pointer items-center gap-3 px-3 py-2 hover:bg-muted/40">
                          <Checkbox checked={checked} onCheckedChange={() => toggle(product)} />
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-sm">{product.name}</span>
                            <span className="text-muted-foreground block truncate font-mono text-xs">
                              {product.barcode ?? product.sku}
                            </span>
                          </span>
                        </label>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <label className="flex items-center gap-2 text-sm">
                Copies
                <Input
                  value={copies}
                  onChange={(event) => setCopies(event.target.value.replace(/[^\d]/g, ""))}
                  inputMode="numeric"
                  className="w-16 text-center"
                  aria-label="Copies per product"
                />
              </label>
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <Checkbox
                  checked={includePrice}
                  onCheckedChange={(state) => setIncludePrice(state === true)}
                />
                Include price
              </label>
            </div>

            <Tabs
              value={layout}
              onValueChange={(next) => setLayout(next as LabelLayout)}
              className="w-fit gap-0"
            >
              <TabsList>
                <TabsTrigger value="thermal">
                  <Tag className="size-4" />
                  Thermal 50×25
                </TabsTrigger>
                <TabsTrigger value="a4">
                  <FileText className="size-4" />
                  A4 sheet
                </TabsTrigger>
              </TabsList>
            </Tabs>

            <p className="text-muted-foreground text-xs">
              {selected.length} product{selected.length === 1 ? "" : "s"} · {run.length} label
              {run.length === 1 ? "" : "s"}
              {fullRun.length > run.length ? ` (capped at ${MAX_LABELS})` : ""}
            </p>
          </div>

          <div className="lbl-doc max-h-[60svh] overflow-auto rounded-md border">
            {run.length === 0 ? (
              <p className="text-muted-foreground p-8 text-center text-sm">
                Select a product to preview its label.
              </p>
            ) : (
              <div ref={previewRef}>
                <LabelSheet labels={run} layout={layout} />
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onClose}>
            Close
          </Button>
          <Button type="button" onClick={handlePrint} disabled={run.length === 0}>
            <Printer className="size-4" />
            Print labels
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
