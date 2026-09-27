"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CreditCard, Lock, Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { PaymentMethodFormDialog } from "@/app/(dashboard)/settings/payment-method-form-dialog";
import { SettingsCard } from "@/app/(dashboard)/settings/settings-card";
import { Can, useCan } from "@/components/auth/can";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { describeError } from "@/lib/api/client";
import { paymentMethodsApi, type PaymentKind, type PaymentMethod } from "@/lib/api/settings";

const KIND_LABEL: Record<PaymentKind, string> = {
  cash: "Cash",
  card: "Card",
  mobile: "Mobile wallet",
  bank: "Bank",
  other: "Other",
};

export function PaymentMethodsSettings() {
  const canRead = useCan("payments:read");
  const canWrite = useCan("payments:write");
  const queryClient = useQueryClient();

  const methodsQuery = useQuery({
    queryKey: ["payment-methods"],
    queryFn: () => paymentMethodsApi.list(),
    enabled: canRead,
  });

  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<PaymentMethod | null>(null);

  const methods = methodsQuery.data?.items ?? [];

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["payment-methods"] });
  }

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(method: PaymentMethod) {
    setEditing(method);
    setFormOpen(true);
  }

  async function handleDelete(method: PaymentMethod) {
    try {
      await paymentMethodsApi.remove(method.id);
      toast.success(`Deleted ${method.name}`);
      invalidate();
    } catch (cause) {
      toast.error(describeError(cause));
    }
  }

  if (!canRead) {
    return (
      <SettingsCard title="Payment methods" description="How customers can pay.">
        <ErrorState
          icon={CreditCard}
          title="You cannot view payment methods"
          description="This section requires the payments:read permission."
        />
      </SettingsCard>
    );
  }

  return (
    <SettingsCard
      title="Payment methods"
      description="The tenders the register offers. Built-in methods can be renamed or deactivated, but not deleted."
      action={
        <Can permission="payments:write">
          <Button onClick={openCreate}>
            <Plus className="size-4" />
            New method
          </Button>
        </Can>
      }
    >
      {methodsQuery.isPending ? (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-10 w-full" />
          ))}
        </div>
      ) : methodsQuery.error ? (
        <ErrorState
          title="Could not load payment methods"
          description={describeError(methodsQuery.error)}
          action={
            <Button variant="outline" onClick={() => void methodsQuery.refetch()}>
              Try again
            </Button>
          }
        />
      ) : methods.length === 0 ? (
        <EmptyState
          icon={CreditCard}
          size="compact"
          title="No payment methods"
          description="Add at least one method so sales can be tendered."
        />
      ) : (
        <div className="overflow-hidden rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Method</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Behaviour</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {methods.map((method) => (
                <TableRow key={method.id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="flex flex-col">
                        <span className="font-medium">{method.name}</span>
                        {method.description ? (
                          <span className="text-muted-foreground truncate text-xs">
                            {method.description}
                          </span>
                        ) : null}
                      </div>
                      {method.is_system ? (
                        <Badge variant="info" className="gap-1">
                          <Lock className="size-3" />
                          Built-in
                        </Badge>
                      ) : null}
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{method.code}</TableCell>
                  <TableCell>
                    <Badge variant="neutral">{KIND_LABEL[method.kind]}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {method.opens_cash_drawer ? (
                        <Badge variant="outline">Cash drawer</Badge>
                      ) : null}
                      {method.requires_reference ? (
                        <Badge variant="outline">Reference</Badge>
                      ) : null}
                      {!method.opens_cash_drawer && !method.requires_reference ? (
                        <span className="text-muted-foreground text-xs">—</span>
                      ) : null}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={method.is_active ? "success" : "outline"}>
                      {method.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span>
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              disabled={!canWrite}
                              onClick={() => openEdit(method)}
                              aria-label={`Edit ${method.name}`}
                            >
                              <Pencil className="size-4" />
                            </Button>
                          </span>
                        </TooltipTrigger>
                        <TooltipContent>
                          {canWrite ? "Edit method" : "Requires payments:write"}
                        </TooltipContent>
                      </Tooltip>

                      <Can permission="payments:write">
                        {method.is_system ? (
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span>
                                <Button
                                  variant="ghost"
                                  size="icon-sm"
                                  disabled
                                  aria-label={`${method.name} cannot be deleted`}
                                >
                                  <Trash2 className="size-4" />
                                </Button>
                              </span>
                            </TooltipTrigger>
                            <TooltipContent>
                              Built-in methods cannot be deleted — deactivate it instead
                            </TooltipContent>
                          </Tooltip>
                        ) : (
                          <ConfirmDialog
                            title={`Delete ${method.name}?`}
                            description="The method is removed for this workspace. This cannot be undone."
                            confirmLabel="Delete method"
                            onConfirm={() => handleDelete(method)}
                            trigger={
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                aria-label={`Delete ${method.name}`}
                              >
                                <Trash2 className="size-4" />
                              </Button>
                            }
                          />
                        )}
                      </Can>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {formOpen ? (
        <PaymentMethodFormDialog
          key={editing?.id ?? "new"}
          method={editing}
          onClose={() => setFormOpen(false)}
          onSaved={invalidate}
        />
      ) : null}
    </SettingsCard>
  );
}
