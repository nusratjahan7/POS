"use client";

import { ShieldAlert } from "lucide-react";

import { BusinessSettings } from "@/app/(dashboard)/settings/business-settings";
import { BranchesSettings } from "@/app/(dashboard)/settings/branches-settings";
import { PaymentMethodsSettings } from "@/app/(dashboard)/settings/payment-methods-settings";
import { RegistersSettings } from "@/app/(dashboard)/settings/registers-settings";
import { useCan } from "@/components/auth/can";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const SECTIONS = [
  { value: "business", label: "Business" },
  { value: "branches", label: "Branches" },
  { value: "registers", label: "Registers" },
  { value: "payment-methods", label: "Payment methods" },
] as const;

export function SettingsClient() {
  const canRead = useCan("settings:read");

  if (!canRead) {
    return (
      <PageContainer>
        <PageHeader
          title="Settings"
          description="The business profile, branches, registers and payment methods."
        />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to settings"
              description="This screen requires the settings:read permission. Ask an administrator to grant you a role that includes it."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Settings"
        description="Everything that describes where and how you trade. These values flow into sales, receipts and reports as those modules ship."
      />

      <Tabs defaultValue="business">
        <TabsList aria-label="Settings sections">
          {SECTIONS.map((section) => (
            <TabsTrigger key={section.value} value={section.value}>
              {section.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="business">
          <BusinessSettings />
        </TabsContent>
        <TabsContent value="branches">
          <BranchesSettings />
        </TabsContent>
        <TabsContent value="registers">
          <RegistersSettings />
        </TabsContent>
        <TabsContent value="payment-methods">
          <PaymentMethodsSettings />
        </TabsContent>
      </Tabs>
    </PageContainer>
  );
}
