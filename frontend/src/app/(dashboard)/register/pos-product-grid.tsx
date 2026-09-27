"use client";

import * as React from "react";
import { ImageIcon, PackageX } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { describeError, mediaUrl } from "@/lib/api/client";
import type { PosProduct } from "@/lib/api/pos";
import { formatMoney, formatQuantity } from "@/lib/format";
import { cn } from "@/lib/utils";

const STOCK_LABEL: Record<PosProduct["stock_status"], string> = {
  in_stock: "In stock",
  low_stock: "Low",
  out_of_stock: "Out",
};

const STOCK_VARIANT: Record<
  PosProduct["stock_status"],
  React.ComponentProps<typeof Badge>["variant"]
> = {
  in_stock: "success",
  low_stock: "warning",
  out_of_stock: "destructive",
};

type PosProductGridProps = {
  products: readonly PosProduct[];
  currency: string;
  isLoading: boolean;
  error: unknown;
  onRetry: () => void;
  onAdd: (product: PosProduct) => void;
  /** Quantities already in the cart, so at-cap products read as "Max". */
  cartQuantities?: Record<string, number>;
};

export function PosProductGrid({
  products,
  currency,
  isLoading,
  error,
  onRetry,
  onAdd,
  cartQuantities,
}: PosProductGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, index) => (
          <Skeleton key={index} className="h-40 w-full" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Could not load products"
        description={describeError(error)}
        action={
          <Button variant="outline" onClick={onRetry}>
            Try again
          </Button>
        }
      />
    );
  }

  if (products.length === 0) {
    return (
      <EmptyState
        icon={PackageX}
        title="No products found"
        description="Try a different search, or pick another category."
      />
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
      {products.map((product) => {
        const price = product.discount_price ?? product.selling_price;
        const onSale = product.discount_price !== null;
        const out = product.stock_status === "out_of_stock";
        const stock = Number(product.stock_quantity);
        const inCart = cartQuantities?.[product.id] ?? 0;
        const atLimit = stock > 0 && inCart >= stock;

        return (
          <Button
            key={product.id}
            type="button"
            variant="outline"
            onClick={() => onAdd(product)}
            className={cn(
              "flex h-auto flex-col items-stretch gap-0 rounded-lg p-0 text-left font-normal",
              "transition-transform duration-150 active:scale-[0.98]",
              (out || atLimit) && "opacity-70",
            )}
          >
            <div className="bg-muted relative flex aspect-[4/3] items-center justify-center overflow-hidden rounded-t-lg border-b">
              {mediaUrl(product.image_url) ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={mediaUrl(product.image_url) as string}
                  alt=""
                  className="size-full object-cover"
                />
              ) : (
                <ImageIcon className="text-muted-foreground size-6" aria-hidden />
              )}
              <Badge
                variant={STOCK_VARIANT[product.stock_status]}
                className="absolute top-1.5 right-1.5"
              >
                {STOCK_LABEL[product.stock_status]}
              </Badge>
              {atLimit ? (
                <Badge variant="neutral" className="absolute top-1.5 left-1.5">
                  Max
                </Badge>
              ) : null}
            </div>

            <div className="flex flex-1 flex-col gap-1 p-2.5">
              <span className="line-clamp-2 text-sm leading-snug font-medium">{product.name}</span>
              <span className="text-muted-foreground truncate font-mono text-[0.6875rem]">
                {product.sku}
              </span>
              <div className="mt-auto flex items-center justify-between gap-2 pt-1">
                <div className="flex items-baseline gap-1.5">
                  <span className="text-sm font-semibold tabular-nums">
                    {formatMoney(price, currency)}
                  </span>
                  {onSale ? (
                    <span className="text-muted-foreground text-xs line-through tabular-nums">
                      {formatMoney(product.selling_price, currency)}
                    </span>
                  ) : null}
                </div>
                <span className="text-muted-foreground text-xs tabular-nums">
                  {formatQuantity(product.stock_quantity)}
                </span>
              </div>
            </div>
          </Button>
        );
      })}
    </div>
  );
}
