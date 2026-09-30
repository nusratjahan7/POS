"use client";

import * as React from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import { brandsApi, categoriesApi } from "@/lib/api/catalog";
import {
  discountsApi,
  type Discount,
  type DiscountPayload,
  type DiscountScope,
  type DiscountType,
} from "@/lib/api/discounts";
import { productsApi } from "@/lib/api/products";

const MONEY_PATTERN = /^\d+(\.\d{1,2})?$/;

type FormState = {
  name: string;
  code: string;
  scope: DiscountScope;
  type: DiscountType;
  value: string;
  minOrder: string;
  maxDiscount: string;
  startsAt: string;
  expiresAt: string;
  usageLimit: string;
  perCustomerLimit: string;
  isActive: boolean;
  firstOrderOnly: boolean;
  excludeDiscounted: boolean;
  freeShipping: boolean;
  productIds: string[];
  categoryIds: string[];
  brandIds: string[];
};

function initial(discount: Discount | null): FormState {
  return {
    name: discount?.name ?? "",
    code: discount?.code ?? "",
    scope: discount?.scope ?? "cart",
    type: discount?.type ?? "percentage",
    value: discount?.value ?? "10",
    minOrder: discount?.min_order_amount ?? "0",
    maxDiscount: discount?.max_discount_amount ?? "",
    startsAt: discount?.starts_at?.slice(0, 10) ?? "",
    expiresAt: discount?.expires_at?.slice(0, 10) ?? "",
    usageLimit: discount?.usage_limit != null ? String(discount.usage_limit) : "",
    perCustomerLimit:
      discount?.per_customer_limit != null ? String(discount.per_customer_limit) : "",
    isActive: discount?.is_active ?? true,
    firstOrderOnly: discount?.first_order_only ?? false,
    excludeDiscounted: discount?.exclude_discounted ?? false,
    freeShipping: discount?.free_shipping ?? false,
    productIds: discount?.product_ids ?? [],
    categoryIds: discount?.category_ids ?? [],
    brandIds: discount?.brand_ids ?? [],
  };
}

function toggle(list: string[], id: string): string[] {
  return list.includes(id) ? list.filter((value) => value !== id) : [...list, id];
}

function TargetList({
  label,
  options,
  selected,
  onToggle,
}: {
  label: string;
  options: { id: string; name: string }[];
  selected: string[];
  onToggle: (id: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-sm font-medium">{label}</span>
      {options.length === 0 ? (
        <span className="text-muted-foreground text-xs">Nothing to choose from yet.</span>
      ) : (
        <div className="flex max-h-36 flex-col gap-1 overflow-y-auto rounded-md border p-2">
          {options.map((option) => (
            <label key={option.id} className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={selected.includes(option.id)}
                onCheckedChange={() => onToggle(option.id)}
              />
              {option.name}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

type DiscountFormDialogProps = {
  discount: Discount | null;
  onClose: () => void;
  onSaved: () => void;
};

/** Create or edit a promotion or coupon. */
export function DiscountFormDialog({ discount, onClose, onSaved }: DiscountFormDialogProps) {
  const [form, setForm] = React.useState<FormState>(() => initial(discount));
  const [error, setError] = React.useState<string | null>(null);

  const productsQuery = useQuery({
    queryKey: ["products", "picker"],
    queryFn: () => productsApi.list({ page_size: 200 }),
  });
  const categoriesQuery = useQuery({
    queryKey: ["categories", "options"],
    queryFn: () => categoriesApi.options(),
  });
  const brandsQuery = useQuery({
    queryKey: ["brands", "options"],
    queryFn: () => brandsApi.options(),
  });

  const products = (productsQuery.data?.items ?? []).map((row) => ({ id: row.id, name: row.name }));
  const categories = categoriesQuery.data ?? [];
  const brands = brandsQuery.data ?? [];

  function patch(next: Partial<FormState>) {
    setForm((current) => ({ ...current, ...next }));
  }

  const mutation = useMutation({
    mutationFn: () => {
      const payload: DiscountPayload = {
        name: form.name.trim(),
        code: form.code.trim() || null,
        scope: form.scope,
        type: form.type,
        value: form.value.trim(),
        min_order_amount: form.minOrder.trim() || "0",
        max_discount_amount: form.maxDiscount.trim() || null,
        starts_at: form.startsAt ? `${form.startsAt}T00:00:00Z` : null,
        expires_at: form.expiresAt ? `${form.expiresAt}T23:59:59Z` : null,
        usage_limit: form.usageLimit.trim() ? Number(form.usageLimit) : null,
        per_customer_limit: form.perCustomerLimit.trim() ? Number(form.perCustomerLimit) : null,
        is_active: form.isActive,
        first_order_only: form.firstOrderOnly,
        exclude_discounted: form.excludeDiscounted,
        free_shipping: form.freeShipping,
        product_ids: form.productIds,
        category_ids: form.categoryIds,
        brand_ids: form.brandIds,
      };
      return discount
        ? discountsApi.update(discount.id, payload)
        : discountsApi.create(payload);
    },
    onSuccess: () => {
      toast.success(discount ? "Discount updated" : "Discount created");
      onSaved();
      onClose();
    },
    onError: (cause) => setError(describeError(cause)),
  });

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!form.name.trim()) {
      setError("Give the discount a name.");
      return;
    }
    if (!MONEY_PATTERN.test(form.value.trim())) {
      setError("Enter a value like 10 or 10.50.");
      return;
    }
    if (form.type === "percentage" && Number(form.value) > 100) {
      setError("A percentage cannot exceed 100.");
      return;
    }
    mutation.mutate();
  }

  return (
    <Dialog open onOpenChange={(next) => !next && !mutation.isPending && onClose()}>
      <DialogContent className="max-h-[85svh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{discount ? "Edit discount" : "New discount"}</DialogTitle>
          <DialogDescription>
            A discount with a code is a coupon the till must quote; one without is applied
            automatically.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
          {error ? (
            <Alert variant="destructive">
              <AlertTitle>Could not save the discount</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Name" htmlFor="discount-name">
              <Input
                id="discount-name"
                value={form.name}
                onChange={(event) => patch({ name: event.target.value })}
                autoComplete="off"
              />
            </Field>

            <Field label="Coupon code" htmlFor="discount-code" hint="Leave blank for an automatic offer.">
              <Input
                id="discount-code"
                value={form.code}
                onChange={(event) => patch({ code: event.target.value })}
                placeholder="e.g. SAVE10"
                autoComplete="off"
              />
            </Field>

            <Field label="Applies to" htmlFor="discount-scope">
              <Select
                value={form.scope}
                onValueChange={(value) => patch({ scope: value as DiscountScope })}
              >
                <SelectTrigger id="discount-scope" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="product">Specific products</SelectItem>
                  <SelectItem value="cart">The whole basket</SelectItem>
                </SelectContent>
              </Select>
            </Field>

            <Field label="Type" htmlFor="discount-type">
              <Select
                value={form.type}
                onValueChange={(value) => patch({ type: value as DiscountType })}
              >
                <SelectTrigger id="discount-type" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="percentage">Percentage</SelectItem>
                  <SelectItem value="fixed">Fixed amount</SelectItem>
                </SelectContent>
              </Select>
            </Field>

            <Field
              label={form.type === "percentage" ? "Value (%)" : "Value (amount)"}
              htmlFor="discount-value"
            >
              <Input
                id="discount-value"
                inputMode="decimal"
                value={form.value}
                onChange={(event) => patch({ value: event.target.value })}
                autoComplete="off"
              />
            </Field>

            <Field label="Minimum order" htmlFor="discount-min">
              <Input
                id="discount-min"
                inputMode="decimal"
                value={form.minOrder}
                onChange={(event) => patch({ minOrder: event.target.value })}
                autoComplete="off"
              />
            </Field>

            <Field label="Maximum discount" htmlFor="discount-max" hint="Optional cap.">
              <Input
                id="discount-max"
                inputMode="decimal"
                value={form.maxDiscount}
                onChange={(event) => patch({ maxDiscount: event.target.value })}
                placeholder="No cap"
                autoComplete="off"
              />
            </Field>

            <Field label="Start date" htmlFor="discount-start" hint="Optional.">
              <Input
                id="discount-start"
                type="date"
                value={form.startsAt}
                onChange={(event) => patch({ startsAt: event.target.value })}
              />
            </Field>

            <Field label="Expiry date" htmlFor="discount-expiry" hint="Optional.">
              <Input
                id="discount-expiry"
                type="date"
                value={form.expiresAt}
                onChange={(event) => patch({ expiresAt: event.target.value })}
              />
            </Field>

            <Field label="Usage limit" htmlFor="discount-usage" hint="Optional, across all sales.">
              <Input
                id="discount-usage"
                inputMode="numeric"
                value={form.usageLimit}
                onChange={(event) => patch({ usageLimit: event.target.value })}
                placeholder="Unlimited"
                autoComplete="off"
              />
            </Field>

            <Field
              label="Per-customer limit"
              htmlFor="discount-per-customer"
              hint="Optional, needs a customer on the sale."
            >
              <Input
                id="discount-per-customer"
                inputMode="numeric"
                value={form.perCustomerLimit}
                onChange={(event) => patch({ perCustomerLimit: event.target.value })}
                placeholder="Unlimited"
                autoComplete="off"
              />
            </Field>
          </div>

          <div className="grid gap-2 sm:grid-cols-2">
            {(
              [
                ["isActive", "Active"],
                ["firstOrderOnly", "First order only"],
                ["excludeDiscounted", "Exclude already-discounted products"],
                ["freeShipping", "Free shipping (no effect yet)"],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="flex items-center gap-2 text-sm">
                <Checkbox
                  checked={form[key]}
                  onCheckedChange={(value) => patch({ [key]: Boolean(value) } as Partial<FormState>)}
                />
                {label}
              </label>
            ))}
          </div>

          {form.scope === "product" ? (
            <div className="grid gap-4 sm:grid-cols-3">
              <TargetList
                label="Products"
                options={products}
                selected={form.productIds}
                onToggle={(id) => patch({ productIds: toggle(form.productIds, id) })}
              />
              <TargetList
                label="Categories"
                options={categories}
                selected={form.categoryIds}
                onToggle={(id) => patch({ categoryIds: toggle(form.categoryIds, id) })}
              />
              <TargetList
                label="Brands"
                options={brands}
                selected={form.brandIds}
                onToggle={(id) => patch({ brandIds: toggle(form.brandIds, id) })}
              />
            </div>
          ) : null}

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? <Spinner /> : null}
              {discount ? "Save changes" : "Create discount"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
