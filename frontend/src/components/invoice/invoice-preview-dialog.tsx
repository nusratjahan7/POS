"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { FileText, Printer, Receipt } from "lucide-react";

import { InvoiceDocument } from "@/components/invoice/invoice-document";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { describeError } from "@/lib/api/client";
import { salesApi } from "@/lib/api/sales";
import { printInvoice } from "@/lib/invoice/print";
import { invoiceCss, type InvoiceVariant } from "@/lib/invoice/styles";

/** Inject the invoice stylesheet for the live preview (no `@page`, so nothing else is affected). */
function useInvoiceStyles(variant: InvoiceVariant) {
  React.useEffect(() => {
    const element = document.createElement("style");
    element.dataset.invoiceStyles = variant;
    element.textContent = invoiceCss(variant, { print: false });
    document.head.appendChild(element);
    return () => {
      element.remove();
    };
  }, [variant]);
}

/**
 * Preview, print and reprint an invoice for any sale.
 *
 * Reachable from the payment success panel and the register's last-sale strip, so
 * any sale id can be reprinted. `Print / Save as PDF` sends the previewed markup
 * to the browser's print dialog, where "Save as PDF" produces the PDF version.
 */
export function InvoicePreviewDialog({
  saleId,
  defaultVariant = "thermal",
  onClose,
}: {
  saleId: string;
  defaultVariant?: InvoiceVariant;
  onClose: () => void;
}) {
  const [variant, setVariant] = React.useState<InvoiceVariant>(defaultVariant);
  const previewRef = React.useRef<HTMLDivElement>(null);
  useInvoiceStyles(variant);

  const receiptQuery = useQuery({
    queryKey: ["sale-receipt", saleId],
    queryFn: () => salesApi.receipt(saleId),
  });
  const receipt = receiptQuery.data;

  function handlePrint() {
    const node = previewRef.current;
    if (!node || !receipt) return;
    printInvoice(node.outerHTML, { title: receipt.sale.sale_number, variant });
  }

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Receipt &amp; invoice</DialogTitle>
          <DialogDescription>
            Pick a layout, then print it or choose &ldquo;Save as PDF&rdquo;. The output is real text
            — nothing is captured as a screenshot.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <Tabs
            value={variant}
            onValueChange={(next) => setVariant(next as InvoiceVariant)}
            className="w-fit gap-0"
          >
            <TabsList>
              <TabsTrigger value="thermal">
                <Receipt className="size-4" />
                Thermal
              </TabsTrigger>
              <TabsTrigger value="a4">
                <FileText className="size-4" />
                A4 invoice
              </TabsTrigger>
            </TabsList>
          </Tabs>
          {receipt ? (
            <span className="text-muted-foreground font-mono text-xs">{receipt.sale.sale_number}</span>
          ) : null}
        </div>

        <div className="bg-muted/40 max-h-[60svh] overflow-auto rounded-md border p-4">
          {receiptQuery.isPending ? (
            <div className="mx-auto flex w-full max-w-[180mm] flex-col gap-3">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-40 w-full" />
              <Skeleton className="h-24 w-3/5 self-end" />
            </div>
          ) : receiptQuery.isError ? (
            <ErrorState
              size="compact"
              title="Could not load the invoice"
              description={describeError(receiptQuery.error)}
              action={
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => void receiptQuery.refetch()}
                >
                  Try again
                </Button>
              }
            />
          ) : receipt ? (
            <InvoiceDocument ref={previewRef} receipt={receipt} variant={variant} />
          ) : null}
        </div>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onClose}>
            Close
          </Button>
          <Button type="button" onClick={handlePrint} disabled={!receipt}>
            <Printer className="size-4" />
            Print / Save as PDF
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
