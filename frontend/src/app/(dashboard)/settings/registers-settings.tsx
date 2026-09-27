"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, ScanLine, Search, ShieldAlert, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { RegisterFormDialog } from "@/app/(dashboard)/settings/register-form-dialog";
import { SettingsCard } from "@/app/(dashboard)/settings/settings-card";
import { Can, useCan } from "@/components/auth/can";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { describeError } from "@/lib/api/client";
import { branchesApi } from "@/lib/api/rbac";
import { businessApi, registersApi, type Register } from "@/lib/api/settings";
import { formatMoney } from "@/lib/format";

const ALL_BRANCHES = "all";

export function RegistersSettings() {
  const canRead = useCan("registers:read");
  const canReadBusiness = useCan("business:read");
  const queryClient = useQueryClient();

  const [search, setSearch] = React.useState("");
  const [query, setQuery] = React.useState("");
  const [branchFilter, setBranchFilter] = React.useState(ALL_BRANCHES);

  React.useEffect(() => {
    const timer = setTimeout(() => setQuery(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const branchesQuery = useQuery({
    queryKey: ["branches", "options"],
    queryFn: () => branchesApi.options(),
    enabled: canRead,
  });
  const businessQuery = useQuery({
    queryKey: ["business"],
    queryFn: () => businessApi.get(),
    enabled: canReadBusiness,
  });

  const registersQuery = useQuery({
    queryKey: ["registers", { query, branchFilter }],
    queryFn: () =>
      registersApi.list({
        search: query,
        branch_id: branchFilter === ALL_BRANCHES ? undefined : branchFilter,
      }),
    enabled: canRead,
  });

  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Register | null>(null);

  const branches = branchesQuery.data ?? [];
  const registers = registersQuery.data?.items ?? [];
  const currency = businessQuery.data?.currency ?? "USD";

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["registers"] });
  }

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(register: Register) {
    setEditing(register);
    setFormOpen(true);
  }

  async function handleDelete(register: Register) {
    try {
      await registersApi.remove(register.id);
      toast.success(`Deleted ${register.name}`);
      invalidate();
    } catch (cause) {
      toast.error(describeError(cause));
    }
  }

  if (!canRead) {
    return (
      <SettingsCard title="Registers" description="The tills sales are rung up on.">
        <ErrorState
          icon={ShieldAlert}
          title="You cannot view registers"
          description="This section requires the registers:read permission."
        />
      </SettingsCard>
    );
  }

  const noBranches = !branchesQuery.isPending && branches.length === 0;

  return (
    <SettingsCard
      title="Registers"
      description="Each register belongs to a branch. Sales, once they exist, are tied to a register and its cashier."
      action={
        <Can permission="registers:write">
          <Button onClick={openCreate} disabled={noBranches}>
            <Plus className="size-4" />
            New register
          </Button>
        </Can>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-3 sm:flex sm:min-w-0 sm:flex-nowrap sm:items-center sm:gap-3 sm:overflow-x-auto sm:pb-0.5">
          <div className="relative col-span-2 w-full sm:max-w-xs">
            <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search registers"
              aria-label="Search registers"
              className="pl-8"
            />
          </div>

          <Select value={branchFilter} onValueChange={setBranchFilter}>
            <SelectTrigger className="w-full sm:w-52" aria-label="Filter by branch">
              <SelectValue placeholder="All branches" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_BRANCHES}>All branches</SelectItem>
              {branches.map((branch) => (
                <SelectItem key={branch.id} value={branch.id}>
                  {branch.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {noBranches ? (
          <EmptyState
            icon={ScanLine}
            size="compact"
            title="Add a branch first"
            description="Registers belong to a branch. Create one on the Branches tab, then come back."
          />
        ) : registersQuery.isPending ? (
          <div className="flex flex-col gap-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={index} className="h-10 w-full" />
            ))}
          </div>
        ) : registersQuery.error ? (
          <ErrorState
            title="Could not load registers"
            description={describeError(registersQuery.error)}
            action={
              <Button variant="outline" onClick={() => void registersQuery.refetch()}>
                Try again
              </Button>
            }
          />
        ) : registers.length === 0 ? (
          <EmptyState
            icon={ScanLine}
            size="compact"
            title={query ? "No registers match that search" : "No registers yet"}
            description={
              query
                ? "Try a different name."
                : "Create a register so sales can be attributed to a till."
            }
          />
        ) : (
          <div className="overflow-hidden rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Register</TableHead>
                  <TableHead>Branch</TableHead>
                  <TableHead className="text-right">Opening balance</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {registers.map((register) => (
                  <TableRow key={register.id}>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-medium">{register.name}</span>
                        <span className="text-muted-foreground text-xs">
                          {register.require_opening_balance
                            ? register.allow_opening_balance_override
                              ? "Opening balance required, editable"
                              : "Opening balance required, fixed"
                            : "No opening balance required"}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">
                      <span>{register.branch.name}</span>
                      <span className="text-muted-foreground ml-2 font-mono text-xs">
                        {register.branch.code}
                      </span>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMoney(register.default_opening_balance, currency)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={register.is_active ? "success" : "outline"}>
                        {register.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-1">
                        <Can permission="registers:write">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => openEdit(register)}
                            aria-label={`Edit ${register.name}`}
                          >
                            <Pencil className="size-4" />
                          </Button>

                          <ConfirmDialog
                            title={`Delete ${register.name}?`}
                            description="The register is removed for this workspace. Historical sales keep their reference."
                            confirmLabel="Delete register"
                            onConfirm={() => handleDelete(register)}
                            trigger={
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                aria-label={`Delete ${register.name}`}
                              >
                                <Trash2 className="size-4" />
                              </Button>
                            }
                          />
                        </Can>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {formOpen ? (
        <RegisterFormDialog
          key={editing?.id ?? "new"}
          register={editing}
          branches={branches}
          defaultBranchId={branchFilter === ALL_BRANCHES ? undefined : branchFilter}
          onClose={() => setFormOpen(false)}
          onSaved={invalidate}
        />
      ) : null}
    </SettingsCard>
  );
}
