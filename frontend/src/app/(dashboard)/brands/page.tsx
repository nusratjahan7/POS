import type { Metadata } from "next";

import { BrandsClient } from "./brands-client";

export const metadata: Metadata = {
  title: "Brands",
};

export default function BrandsPage() {
  return <BrandsClient />;
}
