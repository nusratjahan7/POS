import type { Metadata } from "next";

import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

export const metadata: Metadata = {
  title: "Dashboard",
};

const metrics = [
  { label: "Net sales", hint: "Awaiting first sync" },
  { label: "Transactions", hint: "Awaiting first sync" },
  { label: "Average basket", hint: "Awaiting first sync" },
  { label: "Items sold", hint: "Awaiting first sync" },
];

const foundations = [
  { label: "Design system & tokens", state: "ready" },
  { label: "Application shell", state: "ready" },
  { label: "REST API at /api/v1", state: "ready" },
  { label: "Database & migrations", state: "ready" },
  { label: "Authentication", state: "ready" },
  { label: "Users, roles & permissions", state: "ready" },
  { label: "Store, branches & registers", state: "ready" },
  { label: "Products, categories & brands", state: "ready" },
  { label: "Inventory & stock ledger", state: "ready" },
  { label: "Suppliers & purchases", state: "ready" },
  { label: "Sales", state: "planned" },
] as const;

export default function DashboardPage() {
  return (
    <PageContainer>
      <PageHeader
        title="Dashboard"
        description="Operational overview for the current branch. Figures populate once the sales module is connected."
        actions={
          <>
            <Select defaultValue="all">
              <SelectTrigger className="w-44" aria-label="Branch">
                <SelectValue placeholder="Select branch" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All branches</SelectItem>
              </SelectContent>
            </Select>

            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <Button disabled>New sale</Button>
                </span>
              </TooltipTrigger>
              <TooltipContent>Available once the register module ships</TooltipContent>
            </Tooltip>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <CardHeader>
              <CardTitle className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
                {metric.label}
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-2xl leading-none font-semibold tracking-tight tabular-nums">—</p>
              <p className="text-muted-foreground mt-2 text-xs">{metric.hint}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <div>
              <CardTitle>Registers</CardTitle>
              <CardDescription>
                Terminals and shifts configured for this branch.
              </CardDescription>
            </div>
            <Badge variant="outline">0 registers</Badge>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Register</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Last activity</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell colSpan={3}>
                    <EmptyState
                      size="compact"
                      title="No registers configured"
                      description="Registers are created in Settings → Registers."
                    />
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div>
              <CardTitle>Foundation status</CardTitle>
              <CardDescription>Platform scaffolding delivered so far.</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-2.5">
            {foundations.map((item) => (
              <div key={item.label} className="flex items-center justify-between gap-3">
                <span className="text-sm">{item.label}</span>
                <Badge variant={item.state === "ready" ? "success" : "outline"}>
                  {item.state === "ready" ? "Ready" : "Planned"}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  );
}
