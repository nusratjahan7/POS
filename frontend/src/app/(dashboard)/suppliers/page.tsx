import type { Metadata } from "next";

import { SuppliersClient } from "./suppliers-client";

export const metadata: Metadata = {
  title: "Suppliers",
};

export default function SuppliersPage() {
  return <SuppliersClient />;
}
