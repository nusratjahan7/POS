import type { Metadata } from "next";

import { PurchasesClient } from "./purchases-client";

export const metadata: Metadata = {
  title: "Purchases",
};

export default function PurchasesPage() {
  return <PurchasesClient />;
}
