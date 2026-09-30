"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ChartEmpty } from "@/components/reports/chart-card";
import type { CategorySalesRow } from "@/lib/api/reports";
import { formatMoney } from "@/lib/format";

const MAX_CATEGORIES = 6;

const TOOLTIP_STYLE = {
  background: "var(--card)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  fontSize: 12,
} as const;

/** The biggest categories by net sales. */
export function CategoryBarChart({
  data,
  currency,
}: {
  data: CategorySalesRow[];
  currency: string;
}) {
  const points = data
    .filter((row) => Number(row.net) > 0)
    .slice(0, MAX_CATEGORIES)
    .map((row) => ({ name: row.name, net: Number(row.net) }));

  if (points.length === 0) return <ChartEmpty />;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={points} layout="vertical" margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
        <XAxis
          type="number"
          tickLine={false}
          axisLine={false}
          fontSize={12}
          stroke="var(--muted-foreground)"
        />
        <YAxis
          type="category"
          dataKey="name"
          tickLine={false}
          axisLine={false}
          fontSize={12}
          width={120}
          stroke="var(--muted-foreground)"
        />
        <Tooltip
          formatter={(value: unknown) => formatMoney(Number(value), currency)}
          contentStyle={TOOLTIP_STYLE}
        />
        <Bar dataKey="net" name="Net sales" radius={[0, 4, 4, 0]}>
          {points.map((point, index) => (
            <Cell key={point.name} fill={`var(--chart-${(index % 5) + 1})`} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
