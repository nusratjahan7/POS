import type { Metadata } from "next";

import { CashSessionsClient } from "./cash-sessions-client";

export const metadata: Metadata = {
  title: "Cash Sessions",
};

export default function CashSessionsPage() {
  return <CashSessionsClient />;
}
