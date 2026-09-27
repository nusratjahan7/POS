"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { FormSection } from "@/components/forms/form-section";
import { ImageUpload } from "@/components/forms/image-upload";
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
import { Textarea } from "@/components/ui/textarea";
import { ApiError, describeError } from "@/lib/api/client";
import { brandsApi, categoriesApi } from "@/lib/api/catalog";
import { productsApi, type Product } from "@/lib/api/products";
import { cn } from "@/lib/utils";

const NONE = "none";
const CODE_PATTERN = /^[A-Za-z0-9._-]+$/;
const MONEY_PATTERN = /^\d+(\.\d{1,2})?$/;
const QUANTITY_PATTERN = /^\d+(\.\d{1,3})?$/;

function buildSchema(isEdit: boolean) {
  return z
    .object({
      name: z.string().min(1, "Name is required.").max(200, "Use at most 200 characters."),
      sku: z
        .string()
        .min(1, "SKU is required.")
        .max(64, "Use at most 64 characters.")
        .regex(CODE_PATTERN, "Use letters, digits, dot, hyphen or underscore only."),
      barcode: z
        .string()
        .max(64, "Use at most 64 characters.")
        .refine((value) => value === "" || CODE_PATTERN.test(value), {
          message: "Use letters, digits, dot, hyphen or underscore only.",
        }),
      unit: z.string().min(1, "Unit is required.").max(20, "Use at most 20 characters."),
      description: z.string().max(4000, "Use at most 4000 characters."),
      purchase_price: z.string().regex(MONEY_PATTERN, "Enter an amount like 8.50."),
      selling_price: z.string().regex(MONEY_PATTERN, "Enter an amount like 12.99."),
      discount_price: z
        .string()
        .refine((value) => value === "" || MONEY_PATTERN.test(value), {
          message: "Enter an amount like 10.00.",
        }),
      minimum_stock: z.string().regex(QUANTITY_PATTERN, "Enter a quantity like 5 or 5.5."),
      opening_stock: isEdit
        ? z.string()
        : z.string().regex(QUANTITY_PATTERN, "Enter a quantity like 24."),
    })
    .superRefine((values, ctx) => {
      if (
        values.discount_price !== "" &&
        Number(values.discount_price) > Number(values.selling_price)
      ) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["discount_price"],
          message: "The discount cannot exceed the selling price.",
        });
      }
    });
}

type FormValues = z.infer<ReturnType<typeof buildSchema>>;

type ProductFormDialogProps = {
  /** `null` creates a new product. */
  product: Product | null;
  onClose: () => void;
  onSaved: () => void;
};

/** Mounted fresh for each open (the caller supplies a `key`). */
export function ProductFormDialog({ product, onClose, onSaved }: ProductFormDialogProps) {
  const isEdit = product !== null;
  const schema = React.useMemo(() => buildSchema(isEdit), [isEdit]);

  const [categoryId, setCategoryId] = React.useState(product?.category_id ?? NONE);
  const [brandId, setBrandId] = React.useState(product?.brand_id ?? NONE);
  const [imageUrl, setImageUrl] = React.useState<string | null>(product?.image_url ?? null);
  const [isActive, setIsActive] = React.useState(product?.is_active ?? true);
  const [formError, setFormError] = React.useState<string | null>(null);

  const categoriesQuery = useQuery({
    queryKey: ["categories", "options"],
    queryFn: () => categoriesApi.options(),
  });
  const brandsQuery = useQuery({
    queryKey: ["brands", "options"],
    queryFn: () => brandsApi.options(),
  });

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: product?.name ?? "",
      sku: product?.sku ?? "",
      barcode: product?.barcode ?? "",
      unit: product?.unit ?? "unit",
      description: product?.description ?? "",
      purchase_price: product?.purchase_price ?? "0",
      selling_price: product?.selling_price ?? "0",
      discount_price: product?.discount_price ?? "",
      minimum_stock: product?.minimum_stock ?? "0",
      opening_stock: "0",
    },
  });

  async function onSubmit(values: FormValues) {
    setFormError(null);

    const payload = {
      name: values.name.trim(),
      sku: values.sku.trim(),
      barcode: values.barcode.trim() || null,
      category_id: categoryId === NONE ? null : categoryId,
      brand_id: brandId === NONE ? null : brandId,
      purchase_price: values.purchase_price,
      selling_price: values.selling_price,
      discount_price: values.discount_price.trim() || null,
      unit: values.unit.trim(),
      minimum_stock: values.minimum_stock,
      description: values.description.trim() || null,
      image_url: imageUrl,
      is_active: isActive,
      ...(product ? {} : { opening_stock: values.opening_stock }),
    };

    try {
      if (product) {
        await productsApi.update(product.id, payload);
        toast.success(`Updated ${payload.name}`);
      } else {
        await productsApi.create(payload);
        toast.success(`Created ${payload.name}`, {
          description: "Opening stock recorded. Later stock moves through inventory.",
        });
      }
      onSaved();
      onClose();
    } catch (cause) {
      setFormError(describeError(cause));
      if (cause instanceof ApiError) {
        for (const [field, message] of Object.entries(cause.fieldErrors)) {
          if (
            field === "name" ||
            field === "sku" ||
            field === "barcode" ||
            field === "unit" ||
            field === "description" ||
            field === "discount_price"
          ) {
            setError(field, { message });
          }
        }
      }
    }
  }

  const categories = categoriesQuery.data ?? [];
  const brands = brandsQuery.data ?? [];

  return (
    <Dialog open onOpenChange={(next) => !next && !isSubmitting && onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{product ? `Edit ${product.name}` : "New product"}</DialogTitle>
          <DialogDescription>
            {product
              ? "Prices are exact decimals. Stock only moves through inventory once that module ships."
              : "Prices are exact decimals. Opening stock is recorded once; inventory takes over from there."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5" noValidate>
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not save the product</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <FormSection title="Basic information">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                label="Name"
                htmlFor="product-name"
                error={errors.name?.message}
                className="sm:col-span-2"
              >
                <Input
                  id="product-name"
                  placeholder="Espresso Beans 1kg"
                  autoComplete="off"
                  {...register("name")}
                />
              </Field>

              <Field
                label="SKU"
                htmlFor="product-sku"
                error={errors.sku?.message}
                hint="Your internal product code."
              >
                <Input
                  id="product-sku"
                  placeholder="BEAN-1KG"
                  autoComplete="off"
                  className="font-mono uppercase"
                  {...register("sku")}
                />
              </Field>

              <Field
                label="Barcode"
                htmlFor="product-barcode"
                error={errors.barcode?.message}
                hint="Optional. Scanned at the till."
              >
                <Input
                  id="product-barcode"
                  placeholder="8901234567890"
                  autoComplete="off"
                  className="font-mono"
                  {...register("barcode")}
                />
              </Field>

              <Field label="Category" htmlFor="product-category">
                <Select value={categoryId} onValueChange={setCategoryId}>
                  <SelectTrigger id="product-category" className="w-full">
                    <SelectValue placeholder="Uncategorised" />
                  </SelectTrigger>
                  <SelectContent className="max-h-72">
                    <SelectItem value={NONE}>Uncategorised</SelectItem>
                    {categories.map((category) => (
                      <SelectItem key={category.id} value={category.id}>
                        {category.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>

              <Field label="Brand" htmlFor="product-brand">
                <Select value={brandId} onValueChange={setBrandId}>
                  <SelectTrigger id="product-brand" className="w-full">
                    <SelectValue placeholder="No brand" />
                  </SelectTrigger>
                  <SelectContent className="max-h-72">
                    <SelectItem value={NONE}>No brand</SelectItem>
                    {brands.map((brand) => (
                      <SelectItem key={brand.id} value={brand.id}>
                        {brand.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>

              <Field
                label="Unit"
                htmlFor="product-unit"
                error={errors.unit?.message}
                hint="e.g. unit, kg, litre."
              >
                <Input id="product-unit" placeholder="unit" autoComplete="off" {...register("unit")} />
              </Field>

              <Field
                label="Description"
                htmlFor="product-description"
                error={errors.description?.message}
                className="sm:col-span-2"
              >
                <Textarea
                  id="product-description"
                  rows={2}
                  placeholder="Optional details for staff"
                  {...register("description")}
                />
              </Field>
            </div>
          </FormSection>

          <FormSection
            title="Pricing"
            description="All amounts are stored as exact decimals — never floating point."
          >
            <div className="grid gap-4 sm:grid-cols-3">
              <Field
                label="Purchase price"
                htmlFor="product-purchase-price"
                error={errors.purchase_price?.message}
              >
                <Input
                  id="product-purchase-price"
                  inputMode="decimal"
                  placeholder="8.50"
                  {...register("purchase_price")}
                />
              </Field>

              <Field
                label="Selling price"
                htmlFor="product-selling-price"
                error={errors.selling_price?.message}
              >
                <Input
                  id="product-selling-price"
                  inputMode="decimal"
                  placeholder="12.99"
                  {...register("selling_price")}
                />
              </Field>

              <Field
                label="Discount price"
                htmlFor="product-discount-price"
                error={errors.discount_price?.message}
                hint="Optional. Cannot exceed the selling price."
              >
                <Input
                  id="product-discount-price"
                  inputMode="decimal"
                  placeholder="—"
                  {...register("discount_price")}
                />
              </Field>
            </div>
          </FormSection>

          <FormSection
            title="Inventory"
            description="Minimum stock drives the low-stock warning. Quantities support up to three decimals."
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                label="Minimum stock"
                htmlFor="product-minimum-stock"
                error={errors.minimum_stock?.message}
                hint="Flag the product as low at or below this level."
              >
                <Input
                  id="product-minimum-stock"
                  inputMode="decimal"
                  placeholder="5"
                  {...register("minimum_stock")}
                />
              </Field>

              {product ? (
                <Field
                  label="Current stock"
                  htmlFor="product-stock"
                  hint="Read-only for now — the inventory ledger will own this."
                >
                  <Input
                    id="product-stock"
                    value={product.stock_quantity}
                    readOnly
                    disabled
                    className="tabular-nums"
                  />
                </Field>
              ) : (
                <Field
                  label="Opening stock"
                  htmlFor="product-opening-stock"
                  error={errors.opening_stock?.message}
                  hint="Recorded once, on creation."
                >
                  <Input
                    id="product-opening-stock"
                    inputMode="decimal"
                    placeholder="0"
                    {...register("opening_stock")}
                  />
                </Field>
              )}
            </div>
          </FormSection>

          <FormSection title="Media" description="A single image shown on the product list and till.">
            <ImageUpload
              value={imageUrl}
              onChange={setImageUrl}
              label="Product image"
              hint="PNG, JPEG, WebP or GIF, up to 5 MB."
              disabled={isSubmitting}
            />
          </FormSection>

          <label
            className={cn(
              "flex w-fit cursor-pointer items-center gap-2.5",
              isSubmitting && "cursor-not-allowed opacity-60",
            )}
          >
            <Checkbox
              checked={isActive}
              disabled={isSubmitting}
              onCheckedChange={(state) => setIsActive(state === true)}
            />
            <span className="text-sm">This product is active</span>
          </label>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? <Spinner /> : null}
              {product ? "Save changes" : "Create product"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
