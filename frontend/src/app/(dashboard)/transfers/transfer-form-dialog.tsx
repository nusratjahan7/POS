"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "@/components/auth/auth-provider";
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
import { inventoryApi } from "@/lib/api/inventory";
import { productsApi } from "@/lib/api/products";
import { branchesApi } from "@/lib/api/rbac";
import { transfersApi, type Transfer, type TransferLineInput } from "@/lib/api/transfers";
import { formatQuantity } from "@/lib/format";

type DraftLine = { key: string; productId: string; quantity: string };

let lineKey = 0;
function newLine(productId = "", quantity = ""): DraftLine {
  lineKey += 1;
  return { key: `line-${lineKey}`, productId, quantity };
}

/**
 * Raise or edit a transfer. The source stock is shown per line as a hint, but
 * the authoritative sufficiency check happens when the transfer is shipped —
 * stock can change between raising and shipping.
 */
export function TransferFormDialog({
  transfer,
  onClose,
  onSaved,
}: {
  transfer: Transfer | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { user } = useAuth();

  const branchesQuery = useQuery({
    queryKey: ["branches", "options"],
    queryFn: () => branchesApi.options(),
  });
  const productsQuery = useQuery({
    queryKey: ["products", "options"],
    queryFn: () => productsApi.options(),
  });

  const [fromBranchId, setFromBranchId] = React.useState(
    transfer?.from_branch.id ?? user?.branch_id ?? "",
  );
  const [toBranchId, setToBranchId] = React.useState(transfer?.to_branch.id ?? "");
  const [reference, setReference] = React.useState(transfer?.reference ?? "");
  const [note, setNote] = React.useState(transfer?.note ?? "");
  const [lines, setLines] = React.useState<DraftLine[]>(
    transfer
      ? transfer.items.map((item) => newLine(item.product_id, item.quantity))
      : [newLine()],
  );
  const [formError, setFormError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState<"draft" | "submit" | null>(null);

  const branches = branchesQuery.data ?? [];
  const products = productsQuery.data ?? [];
  // Default the source to the first available branch without an effect: the
  // user's pick wins, otherwise fall back to the first branch in the list.
  const fromValue = fromBranchId || branches[0]?.id || "";

  const stockQuery = useQuery({
    queryKey: ["inventory", "stock", "transfer-source", fromValue],
    queryFn: () => inventoryApi.listStock({ branch_id: fromValue, page_size: 100 }),
    enabled: Boolean(fromValue),
  });
  const onHand = React.useMemo(() => {
    const map = new Map<string, string>();
    for (const level of stockQuery.data?.items ?? []) {
      map.set(level.product.id, level.quantity);
    }
    return map;
  }, [stockQuery.data]);

  function updateLine(key: string, patch: Partial<DraftLine>) {
    setLines((current) => current.map((line) => (line.key === key ? { ...line, ...patch } : line)));
  }

  function buildItems(): TransferLineInput[] | null {
    const items: TransferLineInput[] = [];
    const seen = new Set<string>();
    for (const line of lines) {
      if (!line.productId) continue;
      if (seen.has(line.productId)) {
        setFormError("The same product appears more than once.");
        return null;
      }
      const quantity = line.quantity.trim();
      if (!/^\d+(\.\d{1,3})?$/.test(quantity) || Number(quantity) <= 0) {
        setFormError("Every line needs a quantity greater than zero.");
        return null;
      }
      seen.add(line.productId);
      items.push({ product_id: line.productId, quantity });
    }
    if (items.length === 0) {
      setFormError("Add at least one product to transfer.");
      return null;
    }
    return items;
  }

  async function save(submit: boolean) {
    setFormError(null);
    if (!fromValue || !toBranchId) {
      setFormError("Choose a source and a destination branch.");
      return;
    }
    if (fromValue === toBranchId) {
      setFormError("The source and destination branches must differ.");
      return;
    }
    const items = buildItems();
    if (!items) return;

    setBusy(submit ? "submit" : "draft");
    try {
      if (transfer) {
        await transfersApi.update(transfer.id, {
          from_branch_id: fromValue,
          to_branch_id: toBranchId,
          reference: reference.trim() || null,
          note: note.trim() || null,
          items,
        });
        toast.success(`Updated ${transfer.transfer_number}`);
      } else {
        const created = await transfersApi.create({
          from_branch_id: fromValue,
          to_branch_id: toBranchId,
          reference: reference.trim() || null,
          note: note.trim() || null,
          items,
          submit,
        });
        toast.success(`Created ${created.transfer_number}`, {
          description: submit ? "Sent for approval." : "Saved as a draft.",
        });
      }
      onSaved();
      onClose();
    } catch (cause) {
      setFormError(describeError(cause));
    } finally {
      setBusy(null);
    }
  }

  const disabled = busy !== null;

  return (
    <Dialog open onOpenChange={(next) => !next && !disabled && onClose()}>
      <DialogContent className="max-h-[90vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{transfer ? `Edit ${transfer.transfer_number}` : "New stock transfer"}</DialogTitle>
          <DialogDescription>
            Move stock from one branch to another. Stock leaves the source when the transfer is
            shipped and arrives at the destination when it is received.
          </DialogDescription>
        </DialogHeader>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            void save(false);
          }}
          className="flex flex-col gap-5"
        >
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not save the transfer</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <section className="flex flex-col gap-4">
            <p className="text-sm font-semibold tracking-tight">Branches</p>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="From (source)" htmlFor="transfer-from">
                <Select
                  value={fromValue}
                  onValueChange={(value) => setFromBranchId(value)}
                  disabled={disabled}
                >
                  <SelectTrigger id="transfer-from" className="w-full">
                    <SelectValue placeholder="Select a branch" />
                  </SelectTrigger>
                  <SelectContent>
                    {branches.map((branch) => (
                      <SelectItem key={branch.id} value={branch.id}>
                        {branch.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>

              <Field label="To (destination)" htmlFor="transfer-to">
                <Select
                  value={toBranchId}
                  onValueChange={(value) => setToBranchId(value)}
                  disabled={disabled}
                >
                  <SelectTrigger id="transfer-to" className="w-full">
                    <SelectValue placeholder="Select a branch" />
                  </SelectTrigger>
                  <SelectContent>
                    {branches
                      .filter((branch) => branch.id !== fromValue)
                      .map((branch) => (
                        <SelectItem key={branch.id} value={branch.id}>
                          {branch.name}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </Field>
            </div>
          </section>

          <section className="flex flex-col gap-3">
            <p className="text-sm font-semibold tracking-tight">Items</p>
            <div className="flex flex-col gap-2">
              {lines.map((line) => {
                const available = line.productId ? onHand.get(line.productId) : undefined;
                const short =
                  available !== undefined &&
                  line.quantity !== "" &&
                  Number(line.quantity) > Number(available);
                return (
                  <div key={line.key} className="flex items-start gap-2">
                    <div className="min-w-0 flex-1">
                      <Select
                        value={line.productId}
                        onValueChange={(value) => updateLine(line.key, { productId: value })}
                        disabled={disabled}
                      >
                        <SelectTrigger aria-label="Product" className="w-full">
                          <SelectValue placeholder="Select a product" />
                        </SelectTrigger>
                        <SelectContent>
                          {products.map((product) => (
                            <SelectItem key={product.id} value={product.id}>
                              {product.name} · {product.sku}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {available !== undefined ? (
                        <p className={short ? "text-destructive mt-1 text-xs" : "text-muted-foreground mt-1 text-xs"}>
                          {short ? "Only " : "On hand at source: "}
                          {formatQuantity(available)}
                          {short ? " available at the source." : ""}
                        </p>
                      ) : null}
                    </div>
                    <Input
                      value={line.quantity}
                      onChange={(event) => updateLine(line.key, { quantity: event.target.value })}
                      inputMode="decimal"
                      placeholder="0"
                      aria-label="Quantity"
                      disabled={disabled}
                      className="w-24 tabular-nums"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      aria-label="Remove line"
                      disabled={disabled || lines.length === 1}
                      onClick={() => setLines((current) => current.filter((row) => row.key !== line.key))}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </div>
                );
              })}
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-fit"
              disabled={disabled}
              onClick={() => setLines((current) => [...current, newLine()])}
            >
              <Plus className="size-4" />
              Add item
            </Button>
          </section>

          <section className="flex flex-col gap-4">
            <p className="text-sm font-semibold tracking-tight">Details</p>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Reference" htmlFor="transfer-reference" hint="Optional — a PO or memo.">
                <Input
                  id="transfer-reference"
                  value={reference}
                  onChange={(event) => setReference(event.target.value)}
                  placeholder="e.g. PO-1042"
                  disabled={disabled}
                />
              </Field>
            </div>
            <Field label="Note" htmlFor="transfer-note">
              <Textarea
                id="transfer-note"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Optional instructions for the receiving branch"
                disabled={disabled}
                rows={2}
              />
            </Field>
          </section>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={disabled}>
              Cancel
            </Button>
            {transfer ? (
              <Button type="submit" disabled={disabled}>
                {busy === "draft" ? <Spinner /> : null}
                Save changes
              </Button>
            ) : (
              <>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void save(false)}
                  disabled={disabled}
                >
                  {busy === "draft" ? <Spinner /> : null}
                  Save as draft
                </Button>
                <Button type="button" onClick={() => void save(true)} disabled={disabled}>
                  {busy === "submit" ? <Spinner /> : null}
                  Submit for approval
                </Button>
              </>
            )}
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
