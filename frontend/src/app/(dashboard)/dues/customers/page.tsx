import type { Metadata } from "next";

import { CustomerDuesClient } from "./dues-client";

export const metadata: Metadata = {
  title: "Customer Dues",
};

export default function CustomerDuesPage() {
  return <CustomerDuesClient />;
}
