import type { Metadata } from "next";

import { ExpensesClient } from "./expenses-client";

export const metadata: Metadata = {
  title: "Expenses",
};

export default function ExpensesPage() {
  return <ExpensesClient />;
}
