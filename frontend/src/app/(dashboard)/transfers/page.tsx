import type { Metadata } from "next";

import { TransfersClient } from "./transfers-client";

export const metadata: Metadata = {
  title: "Stock Transfers",
};

export default function TransfersPage() {
  return <TransfersClient />;
}
