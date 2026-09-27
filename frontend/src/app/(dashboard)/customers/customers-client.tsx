"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, Pencil, Plus, ShieldAlert, UserX, Users } from "lucide-react";
import { toast } from "sonner";

import { CustomerDetailsDialog } from "@/app/(dashboard)/customers/customer-details-dialog";
import { CustomerFormDialog } from "@/app/(dashboard)/customers/customer-form-dialog";
import { Can, useCan } from "@/components/auth/can";
import { DataTable, type DataTableColumn } from "@/components/data-table/data-table";
import { DataTablePagination } from "@/components/data-table/data-table-pagination";
import { DataTableSearch } from "@/components/data-table/data-table-search";
import { SelectFilter } from "@/components/data-table/select-filter";
import { useDataTable } from "@/components/data-table/use-data-table";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { ErrorState } from "@/components/ui/error-state";
import { describeError } from "@/lib/api/client";
import { customersApi, type Customer } from "@/lib/api/customers";
import { businessApi } from "@/lib/api/settings";
import { formatMoney } from "@/lib/format";

const ALL = "all";

const STATUS_OPTIONS = [
  { value: ALL, label: "All statuses" },
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
];

export function CustomersClient() {
  const canRead = useCan("customers:read");
  const canWrite = useCan("customers:write");
  const canReadBusiness = useCan("business:read");
  const queryClient = useQueryClient();

  const table = useDataTable();
  const [status, setStatus] = React.useState(ALL);

  const businessQuery = useQuery({
    queryKey: ["business"],
    queryFn: () => businessApi.get(),
    enabled: canReadBusiness,
  });

  const listQuery = useQuery({
    queryKey: ["customers", { query: table.query, page: table.page, status }],
    queryFn: () =>
      customersApi.list({
        search: table.query,
        page: table.page,
        is_active: status === ALL ? undefined : status === "active",
      }),
    enabled: canRead,
  });

  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Customer | null>(null);
  const [detailId, setDetailId] = React.useState<string | null>(null);

  const customers = listQuery.data?.items ?? [];
  const currency = businessQuery.data?.currency ?? "USD";

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["customers"] });
  }

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(customer: Customer) {
    setEditing(customer);
    setFormOpen(true);
  }

  async function handleDeactivate(customer: Customer) {
    try {
      await customersApi.deactivate(customer.id);
      toast.success(`Deactivated ${customer.name}`);
      invalidate();
    } catch (cause) {
      toast.error(describeError(cause));
    }
  }

  const columns: DataTableColumn<Customer>[] = [
    {
      id: "customer",
      header: "Customer",
      cell: (customer) => (
        <div className="flex flex-col">
          <span className="truncate font-medium">{customer.name}</span>
          {customer.phone ? (
            <span className="text-muted-foreground truncate text-xs">{customer.phone}</span>
          ) : null}
        </div>
      ),
    },
    {
      id: "email",
      header: "Email",
      hideBelow: "md",
      cell: (customer) => (
        <span className="text-muted-foreground truncate text-sm">{customer.email ?? "—"}</span>
      ),
    },
    {
      id: "opening_balance",
      header: "Opening",
      align: "right",
      hideBelow: "lg",
      cell: (customer) => (
        <span className="text-muted-foreground text-sm tabular-nums">
          {formatMoney(customer.opening_balance, currency)}
        </span>
      ),
    },
    {
      id: "balance",
      header: "Outstanding",
      align: "right",
      cell: (customer) => (
        <span className="font-medium tabular-nums">{formatMoney(customer.balance, currency)}</span>
      ),
    },
    {
      id: "status",
      header: "Status",
      cell: (customer) => (
        <Badge variant={customer.is_active ? "success" : "outline"}>
          {customer.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      id: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (customer) => (
        <div className="flex items-center justify-end gap-1">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setDetailId(customer.id)}
            aria-label={`View ${customer.name}`}
          >
            <Eye className="size-4" />
          </Button>
          <Can permission="customers:write">
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => openEdit(customer)}
              aria-label={`Edit ${customer.name}`}
            >
              <Pencil className="size-4" />
            </Button>
            <ConfirmDialog
              title={`Deactivate ${customer.name}?`}
              description="The customer is hidden from the list and can no longer be selected. Past records are kept."
              confirmLabel="Deactivate"
              onConfirm={() => handleDeactivate(customer)}
              trigger={
                <Button variant="ghost" size="icon-sm" aria-label={`Deactivate ${customer.name}`}>
                  <UserX className="size-4" />
                </Button>
              }
            />
          </Can>
        </div>
      ),
    },
  ];

  if (!canRead) {
    return (
      <PageContainer>
        <PageHeader title="Customers" description="People who buy from you, and what they owe." />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to customers"
              description="This screen requires the customers:read permission. Ask an administrator to grant you a role that includes it."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Customers"
        description="People who buy from you, with their account balance and payment history."
        actions={
          <Can permission="customers:write">
            <Button onClick={openCreate}>
              <Plus className="size-4" />
              New customer
            </Button>
          </Can>
        }
      />

      <Card>
        <CardHeader className="flex-col items-stretch gap-3 sm:flex-row sm:items-center">
          <div className="shrink-0">
            <CardTitle>All customers</CardTitle>
            <CardDescription>
              {listQuery.data
                ? `${listQuery.data.total} customer${listQuery.data.total === 1 ? "" : "s"}`
                : "Loading customers"}
            </CardDescription>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:flex sm:min-w-0 sm:flex-nowrap sm:items-center sm:gap-3 sm:overflow-x-auto sm:pb-0.5">
            <DataTableSearch
              value={table.search}
              onValueChange={table.setSearch}
              placeholder="Search name, phone or email"
              ariaLabel="Search customers"
              className="col-span-2"
            />
            <SelectFilter
              value={status}
              onValueChange={(value) => {
                setStatus(value);
                table.resetPage();
              }}
              options={STATUS_OPTIONS}
              ariaLabel="Filter by status"
              className="sm:w-44"
            />
          </div>
        </CardHeader>

        <CardContent>
          <DataTable
            columns={columns}
            rows={customers}
            rowKey={(customer) => customer.id}
            isLoading={listQuery.isPending}
            error={listQuery.error}
            onRetry={() => void listQuery.refetch()}
            emptyIcon={Users}
            emptyTitle={table.query ? "No customers match your search" : "No customers yet"}
            emptyDescription={
              table.query
                ? "Try a different name, phone or email."
                : "Add your first customer to start selling on account."
            }
          />

          <DataTablePagination
            page={listQuery.data?.page ?? 1}
            pages={listQuery.data?.pages ?? 1}
            total={listQuery.data?.total}
            onPageChange={table.setPage}
          />
        </CardContent>
      </Card>

      {formOpen ? (
        <CustomerFormDialog
          key={editing?.id ?? "new"}
          customer={editing}
          onClose={() => setFormOpen(false)}
          onSaved={invalidate}
        />
      ) : null}

      {detailId ? (
        <CustomerDetailsDialog
          customerId={detailId}
          onClose={() => setDetailId(null)}
          onChanged={invalidate}
        />
      ) : null}

      {!canWrite ? (
        <p className="text-muted-foreground text-xs">
          Your role can view customers but not change them.
        </p>
      ) : null}
    </PageContainer>
  );
}
