"use client";

import * as React from "react";
import { toast } from "sonner";

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
import { describeError } from "@/lib/api/client";
import {
  inventoryApi,
  type MovementType,
  type StockProduct,
} from "@/lib/api/inventory";
import type { ProductOption } from "@/lib/api/products";
import type { BranchOption } from "@/lib/api/rbac";
import { formatQuantity } from "@/lib/format";

const QUANTITY_PATTERN = /^\d+(\.\d{1,3})?$/;

const TYPE_OPTIONS: { value: MovementType; label: string }[] = [
  { value: "stock_in", label: "Stock in (received)" },
  { value: "stock_out", label: "Stock out (removed)" },
  { value: "damage", label: "Damaged / shrinkage" },
  { value: "adjustment", label: "Adjustment (correction)" },
];

type Direction = "increase" | "decrease";

export type AdjustmentPreset = {
  product: StockProduct;
  branch: BranchOption;
  quantity: string;
};

type StockAdjustmentDialogProps = {
  /** When supplied (e.g. from a stock row) the product and branch are fixed. */
  preset?: AdjustmentPreset;
  products: readonly ProductOption[];
  branches: readonly BranchOption[];
  onClose: () => void;
  onSaved: () => void;
};

/** Mounted fresh for each open (the caller supplies a `key`). */
export function StockAdjustmentDialog({
  preset,
  products,
  branches,
  onClose,
  onSaved,
}: StockAdjustmentDialogProps) {
  const [productId, setProductId] = React.useState(preset?.product.id ?? products[0]?.id ?? "");
  const [branchId, setBranchId] = React.useState(preset?.branch.id ?? branches[0]?.id ?? "");
  const [movementType, setMovementType] = React.useState<MovementType>("stock_in");
  const [direction, setDirection] = React.useState<Direction>("increase");
  const [quantity, setQuantity] = React.useState("");
  const [note, setNote] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);

  const isAdjustment = movementType === "adjustment";
  const sign = movementType === "stock_in" || (isAdjustment && direction === "increase") ? 1 : -1;

  const current =
    preset && preset.product.id === productId ? Number(preset.quantity) : null;

  const delta = QUANTITY_PATTERN.test(quantity) ? sign * Number(quantity) : null;
  const projected = current !== null && delta !== null ? current + delta : null;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setFormError(null);

    if (!productId || !branchId) {
      setError("Select a product and a branch.");
      return;
    }
    if (!QUANTITY_PATTERN.test(quantity) || Number(quantity) <= 0) {
      setError("Enter a quantity like 5 or 2.5.");
      return;
    }
    if (projected !== null && projected < 0) {
      setError("That would take the stock below zero.");
      return;
    }

    const signed = (sign * Number(quantity)).toFixed(3);
    setSaving(true);
    try {
      await inventoryApi.createMovement({
        product_id: productId,
        branch_id: branchId,
        movement_type: movementType,
        quantity: signed,
        note: note.trim() || null,
      });
      toast.success("Stock updated", { description: "A movement was recorded." });
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
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Adjust stock</DialogTitle>
          <DialogDescription>
            Every change is recorded as a movement — stock is never edited directly.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not record the movement</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          {preset ? (
            <div className="bg-muted/50 flex items-center justify-between gap-3 rounded-md border p-3 text-sm">
              <div className="flex min-w-0 flex-col">
                <span className="truncate font-medium">{preset.product.name}</span>
                <span className="text-muted-foreground font-mono text-xs">
                  {preset.product.sku}
                </span>
              </div>
              <div className="text-right">
                <div className="text-muted-foreground text-xs">{preset.branch.name}</div>
                <div className="font-medium tabular-nums">
                  {formatQuantity(preset.quantity)} on hand
                </div>
              </div>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Product" htmlFor="adjustment-product">
                <Select value={productId} onValueChange={setProductId}>
                  <SelectTrigger id="adjustment-product" className="w-full">
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
              </Field>

              <Field label="Branch" htmlFor="adjustment-branch">
                <Select value={branchId} onValueChange={setBranchId}>
                  <SelectTrigger id="adjustment-branch" className="w-full">
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
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Movement" htmlFor="adjustment-type">
              <Select
                value={movementType}
                onValueChange={(value) => setMovementType(value as MovementType)}
              >
                <SelectTrigger id="adjustment-type" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TYPE_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            {isAdjustment ? (
              <Field label="Direction" htmlFor="adjustment-direction">
                <Select
                  value={direction}
                  onValueChange={(value) => setDirection(value as Direction)}
                >
                  <SelectTrigger id="adjustment-direction" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="increase">Increase</SelectItem>
                    <SelectItem value="decrease">Decrease</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
            ) : (
              <div className="hidden sm:block" />
            )}
          </div>

          <Field
            label="Quantity"
            htmlFor="adjustment-quantity"
            error={error}
            hint="Up to three decimals."
          >
            <Input
              id="adjustment-quantity"
              inputMode="decimal"
              placeholder="0"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              autoComplete="off"
            />
          </Field>

          {projected !== null ? (
            <p className="text-muted-foreground text-sm">
              New on hand:{" "}
              <span className="text-foreground font-medium tabular-nums">
                {formatQuantity(projected)}
              </span>
            </p>
          ) : null}

          <Field label="Note" htmlFor="adjustment-note" hint="Optional.">
            <Input
              id="adjustment-note"
              placeholder="e.g. stock count correction"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              autoComplete="off"
            />
          </Field>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? <Spinner /> : null}
              Record movement
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
