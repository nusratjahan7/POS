import type { Metadata } from "next";

import { SupplierDuesClient } from "./dues-client";

export const metadata: Metadata = {
  title: "Supplier Dues",
};

export default function SupplierDuesPage() {
  return <SupplierDuesClient />;
}
