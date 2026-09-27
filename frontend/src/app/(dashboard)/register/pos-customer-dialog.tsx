"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, UserPlus, UserRound } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { describeError, ApiError } from "@/lib/api/client";
import { customersApi } from "@/lib/api/customers";
import type { PosCustomer } from "@/lib/pos/cart-store";
import { formatMoney } from "@/lib/format";

type PosCustomerDialogProps = {
  current: PosCustomer | null;
  currency: string;
  onSelect: (customer: PosCustomer | null) => void;
  onClose: () => void;
};

export function PosCustomerDialog({
  current,
  currency,
  onSelect,
  onClose,
}: PosCustomerDialogProps) {
  const queryClient = useQueryClient();
  const [search, setSearch] = React.useState("");
  const [query, setQuery] = React.useState("");

  React.useEffect(() => {
    const timer = setTimeout(() => setQuery(search), 250);
    return () => clearTimeout(timer);
  }, [search]);

  const [name, setName] = React.useState("");
  const [phone, setPhone] = React.useState("");
  const [creating, setCreating] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const customersQuery = useQuery({
    queryKey: ["pos", "customers", query],
    queryFn: () => customersApi.list({ search: query, page_size: 8 }),
  });

  function choose(customer: { id: string; name: string; balance: string }) {
    onSelect({ id: customer.id, name: customer.name, balance: customer.balance });
  }

  async function quickCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (name.trim().length === 0) {
      setError("A name is required.");
      return;
    }
    setCreating(true);
    try {
      const created = await customersApi.create({
        name: name.trim(),
        phone: phone.trim() || null,
      });
      toast.success(`Added ${created.name}`);
      void queryClient.invalidateQueries({ queryKey: ["customers"] });
      choose(created);
    } catch (cause) {
      setError(cause instanceof ApiError ? describeError(cause) : "Could not create the customer.");
    } finally {
      setCreating(false);
    }
  }

  const customers = customersQuery.data?.items ?? [];

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Customer</DialogTitle>
          <DialogDescription>
            Attach an existing customer, add a new one, or keep it as a walk-in sale.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <Button
              variant={current === null ? "default" : "outline"}
              size="sm"
              onClick={() => onSelect(null)}
            >
              <UserRound className="size-4" />
              Walk-in
            </Button>
            {current ? (
              <span className="text-muted-foreground text-xs">Selected: {current.name}</span>
            ) : null}
          </div>

          <div className="relative">
            <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2" />
            <Input
              autoFocus
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search customers by name, phone or email"
              aria-label="Search customers"
              className="pl-8"
            />
          </div>

          <div className="max-h-56 overflow-y-auto rounded-md border">
            {customersQuery.isPending ? (
              <div className="flex flex-col gap-2 p-3">
                {Array.from({ length: 3 }).map((_, index) => (
                  <Skeleton key={index} className="h-9 w-full" />
                ))}
              </div>
            ) : customers.length === 0 ? (
              <EmptyState
                size="compact"
                title={query ? "No customers match" : "No customers yet"}
                description="Add one below to start selling on account."
              />
            ) : (
              <ul className="divide-y">
                {customers.map((customer) => (
                  <li key={customer.id}>
                    <button
                      type="button"
                      onClick={() => choose(customer)}
                      className="hover:bg-accent/60 focus-visible:ring-ring/60 flex w-full items-center justify-between gap-3 px-3 py-2 text-left transition-colors outline-none focus-visible:ring-2"
                    >
                      <span className="flex min-w-0 flex-col">
                        <span className="truncate text-sm font-medium">{customer.name}</span>
                        <span className="text-muted-foreground truncate text-xs">
                          {customer.phone ?? customer.email ?? "—"}
                        </span>
                      </span>
                      {Number(customer.balance) !== 0 ? (
                        <span className="text-muted-foreground shrink-0 text-xs tabular-nums">
                          Owes {formatMoney(customer.balance, currency)}
                        </span>
                      ) : null}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <form onSubmit={quickCreate} className="flex flex-col gap-3 rounded-md border p-3">
            <p className="flex items-center gap-1.5 text-sm font-medium">
              <UserPlus className="size-4" aria-hidden />
              Quick add
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Name" htmlFor="pos-customer-name" error={error}>
                <Input
                  id="pos-customer-name"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Jane Doe"
                  autoComplete="off"
                />
              </Field>
              <Field label="Phone" htmlFor="pos-customer-phone">
                <Input
                  id="pos-customer-phone"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                  placeholder="Optional"
                  autoComplete="off"
                />
              </Field>
            </div>
            <Button type="submit" size="sm" disabled={creating} className="self-start">
              {creating ? "Adding…" : "Add and select"}
            </Button>
          </form>
        </div>
      </DialogContent>
    </Dialog>
  );
}
