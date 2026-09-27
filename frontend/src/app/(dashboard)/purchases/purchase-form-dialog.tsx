"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { toast } from "sonner";

import { FormSection } from "@/components/forms/form-section";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { describeError } from "@/lib/api/client";
import { productsApi } from "@/lib/api/products";
import { purchasesApi, type EditablePurchaseStatus, type Purchase } from "@/lib/api/purchases";
import { branchesApi } from "@/lib/api/rbac";
import { suppliersApi } from "@/lib/api/suppliers";

const MONEY_PATTERN = /^\d+(\.\d{1,2})?$/;
const QUANTITY_PATTERN = /^\d+(\.\d{1,3})?$/;

type Line = {
  key: string;
  productId: string;
  quantity: string;
  unitPrice: string;
};

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function newLine(): Line {
  return { key: Math.random().toString(36).slice(2), productId: "", quantity: "1", unitPrice: "0" };
}

function toNumber(value: string): number {
  return MONEY_PATTERN.test(value) ? Number(value) : 0;
}

type PurchaseFormDialogProps = {
  /** `null` creates a new purchase; a value edits an existing draft/pending one. */
  purchase: Purchase | null;
  onClose: () => void;
  onSaved: () => void;
};

export function PurchaseFormDialog({ purchase, onClose, onSaved }: PurchaseFormDialogProps) {
  const queryClient = useQueryClient();
  const canReadCatalog = true;

  const [supplierId, setSupplierId] = React.useState(purchase?.supplier.id ?? "");
  const [branchId, setBranchId] = React.useState(purchase?.branch.id ?? "");
  const [purchaseDate, setPurchaseDate] = React.useState(
    purchase?.purchase_date ?? today(),
  );
  const [status, setStatus] = React.useState<EditablePurchaseStatus>(
    (purchase?.status as EditablePurchaseStatus) ?? "draft",
  );
  const [note, setNote] = React.useState(purchase?.note ?? "");
  const [discount, setDiscount] = React.useState(purchase?.discount ?? "0");
  const [tax, setTax] = React.useState(purchase?.tax ?? "0");
  const [paid, setPaid] = React.useState(purchase?.paid ?? "0");
  const [lines, setLines] = React.useState<Line[]>(
    purchase
      ? purchase.items.map((item) => ({
          key: item.id,
          productId: item.product.id,
          quantity: item.quantity,
          unitPrice: item.unit_price,
        }))
      : [newLine()],
  );
  const [error, setError] = React.useState<string | null>(null);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);

  const suppliersQuery = useQuery({
    queryKey: ["suppliers", "options"],
    queryFn: () => suppliersApi.options(),
  });
  const branchesQuery = useQuery({
    queryKey: ["branches", "options"],
    queryFn: () => branchesApi.options(),
  });
  const productsQuery = useQuery({
    queryKey: ["products", "options"],
    queryFn: () => productsApi.options(),
    enabled: canReadCatalog,
  });

  const suppliers = suppliersQuery.data ?? [];
  const branches = branchesQuery.data ?? [];
  const products = productsQuery.data ?? [];

  // Default to the first option once the pickers load, without writing state in
  // an effect (the choice is a fallback, not something the user has set).
  const effectiveSupplierId = supplierId || suppliers[0]?.id || "";
  const effectiveBranchId = branchId || branches[0]?.id || "";

  const subtotal = lines.reduce(
    (sum, line) => sum + (QUANTITY_PATTERN.test(line.quantity) ? Number(line.quantity) : 0) * toNumber(line.unitPrice),
    0,
  );
  const total = Math.max(subtotal - toNumber(discount) + toNumber(tax), 0);
  const due = Math.max(total - toNumber(paid), 0);

  function updateLine(key: string, patch: Partial<Line>) {
    setLines((current) => current.map((line) => (line.key === key ? { ...line, ...patch } : line)));
  }

  function removeLine(key: string) {
    setLines((current) => (current.length > 1 ? current.filter((line) => line.key !== key) : current));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setFormError(null);

    if (!effectiveSupplierId) return setError("Choose a supplier.");
    if (!effectiveBranchId) return setError("Choose a branch.");
    if (!purchaseDate) return setError("Choose a purchase date.");

    const cleaned = lines.filter((line) => line.productId !== "");
    if (cleaned.length === 0) return setError("Add at least one product.");
    for (const line of cleaned) {
      if (!QUANTITY_PATTERN.test(line.quantity) || Number(line.quantity) <= 0) {
        return setError("Each quantity must be greater than zero.");
      }
      if (!MONEY_PATTERN.test(line.unitPrice)) {
        return setError("Each purchase price must be a valid amount.");
      }
    }
    if (new Set(cleaned.map((line) => line.productId)).size !== cleaned.length) {
      return setError("The same product cannot appear twice.");
    }
    if (!MONEY_PATTERN.test(discount) || !MONEY_PATTERN.test(tax) || !MONEY_PATTERN.test(paid)) {
      return setError("Discount, tax and paid must be valid amounts.");
    }

    const payload = {
      supplier_id: effectiveSupplierId,
      branch_id: effectiveBranchId,
      purchase_date: purchaseDate,
      discount: discount || "0",
      tax: tax || "0",
      paid: paid || "0",
      status,
      note: note.trim() || null,
      items: cleaned.map((line) => ({
        product_id: line.productId,
        quantity: line.quantity,
        unit_price: line.unitPrice,
      })),
    };

    setSaving(true);
    try {
      if (purchase) {
        await purchasesApi.update(purchase.id, payload);
        toast.success(`Updated ${purchase.purchase_number}`);
      } else {
        const created = await purchasesApi.create(payload);
        toast.success(`Created ${created.purchase_number}`, {
          description: "Receive it to move stock.",
        });
      }
      void queryClient.invalidateQueries({ queryKey: ["purchases"] });
      onSaved();
      onClose();
    } catch (cause) {
      setFormError(describeError(cause));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open onOpenChange={(next) => !next && !saving && onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{purchase ? `Edit ${purchase.purchase_number}` : "New purchase"}</DialogTitle>
          <DialogDescription>
            Raising a purchase does not move stock. Stock increases only when you receive it.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5" noValidate>
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not save the purchase</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <FormSection title="Order details">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Supplier" htmlFor="purchase-supplier">
                <Select value={effectiveSupplierId} onValueChange={setSupplierId}>
                  <SelectTrigger id="purchase-supplier" className="w-full">
                    <SelectValue placeholder="Select a supplier" />
                  </SelectTrigger>
                  <SelectContent className="max-h-72">
                    {suppliers.map((supplier) => (
                      <SelectItem key={supplier.id} value={supplier.id}>
                        {supplier.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>

              <Field label="Branch" htmlFor="purchase-branch" hint="Where the stock will be received.">
                <Select value={effectiveBranchId} onValueChange={setBranchId}>
                  <SelectTrigger id="purchase-branch" className="w-full">
                    <SelectValue placeholder="Select a branch" />
                  </SelectTrigger>
                  <SelectContent className="max-h-72">
                    {branches.map((branch) => (
                      <SelectItem key={branch.id} value={branch.id}>
                        {branch.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>

              <Field label="Purchase date" htmlFor="purchase-date">
                <Input
                  id="purchase-date"
                  type="date"
                  value={purchaseDate}
                  onChange={(event) => setPurchaseDate(event.target.value)}
                />
              </Field>

              <Field label="Status" htmlFor="purchase-status">
                <Select value={status} onValueChange={(value) => setStatus(value as EditablePurchaseStatus)}>
                  <SelectTrigger id="purchase-status" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="draft">Draft</SelectItem>
                    <SelectItem value="pending">Pending</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
            </div>
          </FormSection>

          <FormSection title="Items">
            <div className="flex flex-col gap-3">
              {lines.map((line) => (
                <div key={line.key} className="grid grid-cols-12 items-end gap-2">
                  <div className="col-span-12 sm:col-span-6">
                    <Select
                      value={line.productId}
                      onValueChange={(value) => updateLine(line.key, { productId: value })}
                    >
                      <SelectTrigger className="w-full" aria-label="Product">
                        <SelectValue placeholder="Select a product" />
                      </SelectTrigger>
                      <SelectContent className="max-h-72">
                        {products.map((product) => (
                          <SelectItem key={product.id} value={product.id}>
                            {product.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="col-span-4 sm:col-span-2">
                    <Input
                      inputMode="decimal"
                      placeholder="Qty"
                      aria-label="Quantity"
                      value={line.quantity}
                      onChange={(event) => updateLine(line.key, { quantity: event.target.value })}
                    />
                  </div>
                  <div className="col-span-5 sm:col-span-3">
                    <Input
                      inputMode="decimal"
                      placeholder="Unit cost"
                      aria-label="Unit cost"
                      value={line.unitPrice}
                      onChange={(event) => updateLine(line.key, { unitPrice: event.target.value })}
                    />
                  </div>
                  <div className="col-span-3 flex justify-end sm:col-span-1">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => removeLine(line.key)}
                      disabled={lines.length === 1}
                      aria-label="Remove line"
                    >
                      <X className="size-4" />
                    </Button>
                  </div>
                </div>
              ))}

              <Button type="button" variant="outline" size="sm" onClick={() => setLines((c) => [...c, newLine()])}>
                <Plus className="size-4" />
                Add item
              </Button>
            </div>
          </FormSection>

          <FormSection title="Totals">
            <div className="grid gap-4 sm:grid-cols-3">
              <Field label="Discount" htmlFor="purchase-discount">
                <Input
                  id="purchase-discount"
                  inputMode="decimal"
                  value={discount}
                  onChange={(event) => setDiscount(event.target.value)}
                />
              </Field>
              <Field label="Tax" htmlFor="purchase-tax">
                <Input
                  id="purchase-tax"
                  inputMode="decimal"
                  value={tax}
                  onChange={(event) => setTax(event.target.value)}
                />
              </Field>
              <Field label="Paid" htmlFor="purchase-paid">
                <Input
                  id="purchase-paid"
                  inputMode="decimal"
                  value={paid}
                  onChange={(event) => setPaid(event.target.value)}
                />
              </Field>
            </div>

            <div className="bg-muted/40 grid grid-cols-2 gap-2 rounded-md border p-3 text-sm sm:grid-cols-4">
              <div>
                <div className="text-muted-foreground text-xs">Subtotal</div>
                <div className="font-medium tabular-nums">{subtotal.toFixed(2)}</div>
              </div>
              <div>
                <div className="text-muted-foreground text-xs">Total</div>
                <div className="font-medium tabular-nums">{total.toFixed(2)}</div>
              </div>
              <div>
                <div className="text-muted-foreground text-xs">Due</div>
                <div className="font-medium tabular-nums">{due.toFixed(2)}</div>
              </div>
            </div>

            <Field label="Note" htmlFor="purchase-note" hint="Optional.">
              <Textarea
                id="purchase-note"
                rows={2}
                placeholder="e.g. delivery by Friday"
                value={note}
                onChange={(event) => setNote(event.target.value)}
              />
            </Field>

            {error ? <p className="text-destructive text-xs">{error}</p> : null}
          </FormSection>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? <Spinner /> : null}
              {purchase ? "Save changes" : "Create purchase"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
