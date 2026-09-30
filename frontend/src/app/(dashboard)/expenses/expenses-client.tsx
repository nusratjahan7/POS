"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Banknote, Settings2, ShieldAlert, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { ExpenseCategoryDialog } from "@/app/(dashboard)/expenses/expense-category-dialog";
import { ExpenseFormDialog } from "@/app/(dashboard)/expenses/expense-form-dialog";
import { PickedDateRange, SalesDateRange } from "@/app/(dashboard)/sales/sales-date-range";
import { Can, useCan } from "@/components/auth/can";
import { DataTable, type DataTableColumn } from "@/components/data-table/data-table";
import { DataTablePagination } from "@/components/data-table/data-table-pagination";
import { DataTableSearch } from "@/components/data-table/data-table-search";
import { SelectFilter } from "@/components/data-table/select-filter";
import { useDataTable } from "@/components/data-table/use-data-table";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { ErrorState } from "@/components/ui/error-state";
import { describeError } from "@/lib/api/client";
import { expenseCategoriesApi, expensesApi, type Expense } from "@/lib/api/expenses";
import { branchesApi } from "@/lib/api/rbac";
import { businessApi, paymentMethodsApi } from "@/lib/api/settings";
import { formatMoney } from "@/lib/format";

const ALL = "all";

function isoDay(value: PickedDateRange["start"] | undefined): string | undefined {
  return value ? value.toString().slice(0, 10) : undefined;
}

export function ExpensesClient() {
  const canRead = useCan("expenses:read");
  const queryClient = useQueryClient();

  const table = useDataTable();
  const [branch, setBranch] = React.useState(ALL);
  const [category, setCategory] = React.useState(ALL);
  const [method, setMethod] = React.useState(ALL);
  const [range, setRange] = React.useState<PickedDateRange | null>(null);
  const [formOpen, setFormOpen] = React.useState(false);
  const [categoriesOpen, setCategoriesOpen] = React.useState(false);

  const dateFrom = isoDay(range?.start);
  const dateTo = isoDay(range?.end);

  const businessQuery = useQuery({ queryKey: ["business"], queryFn: () => businessApi.get() });
  const branchesQuery = useQuery({
    queryKey: ["branches", "options"],
    queryFn: () => branchesApi.options(),
    enabled: canRead,
  });
  const categoriesQuery = useQuery({
    queryKey: ["expense-categories", "options"],
    queryFn: () => expenseCategoriesApi.options(),
    enabled: canRead,
  });
  const methodsQuery = useQuery({
    queryKey: ["payment-methods", "options"],
    queryFn: () => paymentMethodsApi.options(),
    enabled: canRead,
  });

  const filters = {
    search: table.query || undefined,
    branch_id: branch === ALL ? undefined : branch,
    category_id: category === ALL ? undefined : category,
    payment_method_id: method === ALL ? undefined : method,
    date_from: dateFrom,
    date_to: dateTo,
  };

  const listQuery = useQuery({
    queryKey: ["expenses", { ...filters, page: table.page }],
    queryFn: () => expensesApi.list({ ...filters, page: table.page }),
    enabled: canRead,
  });
  const totalQuery = useQuery({
    queryKey: ["expenses", "total", filters],
    queryFn: () => expensesApi.total(filters),
    enabled: canRead,
  });

  const expenses = listQuery.data?.items ?? [];
  const currency = businessQuery.data?.currency ?? "USD";

  const removeMutation = useMutation({
    mutationFn: (expenseId: string) => expensesApi.remove(expenseId),
    onSuccess: () => {
      toast.success("Expense removed");
      void queryClient.invalidateQueries({ queryKey: ["expenses"] });
    },
    onError: (cause) => toast.error(describeError(cause)),
  });

  const toOptions = (rows: { id: string; name: string }[]) => [
    { value: ALL, label: "All" },
    ...rows.map((row) => ({ value: row.id, label: row.name })),
  ];

  const columns: DataTableColumn<Expense>[] = [
    {
      id: "date",
      header: "Date",
      cell: (expense) => <span className="text-sm tabular-nums">{expense.spent_at}</span>,
    },
    {
      id: "category",
      header: "Category",
      cell: (expense) => <span className="text-sm font-medium">{expense.category.name}</span>,
    },
    {
      id: "description",
      header: "Description",
      hideBelow: "md",
      cell: (expense) => (
        <span className="text-muted-foreground truncate text-sm">
          {expense.description ?? expense.reference ?? "—"}
        </span>
      ),
    },
    {
      id: "method",
      header: "Method",
      hideBelow: "lg",
      cell: (expense) => <span className="text-sm">{expense.payment_method.name}</span>,
    },
    {
      id: "branch",
      header: "Branch",
      hideBelow: "lg",
      cell: (expense) => (
        <span className="text-muted-foreground text-sm">{expense.branch.name}</span>
      ),
    },
    {
      id: "amount",
      header: "Amount",
      align: "right",
      cell: (expense) => (
        <span className="font-medium tabular-nums">{formatMoney(expense.amount, currency)}</span>
      ),
    },
    {
      id: "actions",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      cell: (expense) => (
        <Can permission="expenses:write">
          <ConfirmDialog
            title="Remove this expense?"
            description="Deleting reverses its effect on an open register's drawer. Expenses on a closed register cannot be removed."
            confirmLabel="Remove expense"
            onConfirm={() => removeMutation.mutateAsync(expense.id)}
            trigger={
              <Button variant="ghost" size="icon-sm" aria-label="Remove expense">
                <Trash2 className="size-4" />
              </Button>
            }
          />
        </Can>
      ),
    },
  ];

  if (!canRead) {
    return (
      <PageContainer>
        <PageHeader title="Expenses" description="What the business spends." />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to expenses"
              description="This screen requires the expenses:read permission. Ask an administrator to grant you a role that includes it."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Expenses"
        description="Every cost, filed by category and settled by a payment method."
        actions={
          <div className="flex items-center gap-2">
            <Can permission="expenses:write">
              <Button variant="outline" onClick={() => setCategoriesOpen(true)}>
                <Settings2 className="size-4" />
                Categories
              </Button>
              <Button onClick={() => setFormOpen(true)}>
                <Banknote className="size-4" />
                New expense
              </Button>
            </Can>
          </div>
        }
      />

      <Card>
        <CardHeader className="flex-col items-stretch gap-3 lg:flex-row lg:items-center">
          <div className="shrink-0">
            <CardTitle>All expenses</CardTitle>
            <CardDescription>
              {listQuery.data
                ? `${listQuery.data.total} record${listQuery.data.total === 1 ? "" : "s"} · ${formatMoney(
                    totalQuery.data?.amount ?? "0",
                    currency,
                  )} total`
                : "Loading expenses"}
            </CardDescription>
          </div>
          <div className="grid grid-cols-2 gap-3 lg:flex lg:min-w-0 lg:flex-nowrap lg:items-center lg:gap-3 lg:overflow-x-auto">
            <DataTableSearch
              value={table.search}
              onValueChange={table.setSearch}
              placeholder="Search description or reference"
              ariaLabel="Search expenses"
              className="col-span-2"
            />
            <SalesDateRange value={range} onChange={setRange} />
            <SelectFilter
              value={category}
              onValueChange={(value) => {
                setCategory(value);
                table.resetPage();
              }}
              options={toOptions(categoriesQuery.data ?? [])}
              ariaLabel="Filter by category"
              className="sm:w-44"
            />
            <SelectFilter
              value={method}
              onValueChange={(value) => {
                setMethod(value);
                table.resetPage();
              }}
              options={toOptions(methodsQuery.data ?? [])}
              ariaLabel="Filter by payment method"
              className="sm:w-44"
            />
            <SelectFilter
              value={branch}
              onValueChange={(value) => {
                setBranch(value);
                table.resetPage();
              }}
              options={toOptions(branchesQuery.data ?? [])}
              ariaLabel="Filter by branch"
              className="sm:w-44"
            />
          </div>
        </CardHeader>

        <CardContent>
          <DataTable
            columns={columns}
            rows={expenses}
            rowKey={(expense) => expense.id}
            isLoading={listQuery.isPending}
            error={listQuery.error}
            onRetry={() => void listQuery.refetch()}
            emptyIcon={Banknote}
            emptyTitle={table.query ? "No expenses match your search" : "No expenses yet"}
            emptyDescription={
              table.query
                ? "Try a different description or reference."
                : "Recorded expenses will appear here."
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
        <ExpenseFormDialog
          onClose={() => setFormOpen(false)}
          onSaved={() => {
            void queryClient.invalidateQueries({ queryKey: ["expenses"] });
            void queryClient.invalidateQueries({ queryKey: ["register-sessions"] });
          }}
        />
      ) : null}

      {categoriesOpen ? (
        <ExpenseCategoryDialog onClose={() => setCategoriesOpen(false)} />
      ) : null}
    </PageContainer>
  );
}
