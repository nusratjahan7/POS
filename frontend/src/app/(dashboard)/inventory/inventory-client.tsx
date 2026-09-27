"use client";

import { ShieldAlert } from "lucide-react";

import { MovementsTab } from "@/app/(dashboard)/inventory/movements-tab";
import { StockTab } from "@/app/(dashboard)/inventory/stock-tab";
import { useCan } from "@/components/auth/can";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export function InventoryClient() {
  const canRead = useCan("inventory:read");

  if (!canRead) {
    return (
      <PageContainer>
        <PageHeader title="Inventory" description="Stock on hand and how it changes." />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to inventory"
              description="This screen requires the inventory:read permission. Ask an administrator to grant you a role that includes it."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Inventory"
        description="Stock is only ever changed by recording a movement. Every adjustment, receipt and loss leaves a permanent entry in the ledger."
      />

      <Tabs defaultValue="stock">
        <TabsList aria-label="Inventory sections">
          <TabsTrigger value="stock">Stock on hand</TabsTrigger>
          <TabsTrigger value="movements">Movement history</TabsTrigger>
        </TabsList>

        <TabsContent value="stock">
          <StockTab />
        </TabsContent>
        <TabsContent value="movements">
          <MovementsTab />
        </TabsContent>
      </Tabs>
    </PageContainer>
  );
}
