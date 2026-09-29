import type { Metadata } from "next";

import { SalesClient } from "./sales-client";

export const metadata: Metadata = { title: "Sales" };

export default function SalesPage() {
  return <SalesClient />;
}
