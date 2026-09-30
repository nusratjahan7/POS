import type { Metadata } from "next";

import { DiscountsClient } from "./discounts-client";

export const metadata: Metadata = {
  title: "Discounts",
};

export default function DiscountsPage() {
  return <DiscountsClient />;
}
