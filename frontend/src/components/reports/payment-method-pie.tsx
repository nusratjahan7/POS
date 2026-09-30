"use client";

import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { ChartEmpty } from "@/components/reports/chart-card";
import type { PaymentMethodSalesRow } from "@/lib/api/reports";
import { formatMoney } from "@/lib/format";

const TOOLTIP_STYLE = {
  background: "var(--card)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  fontSize: 12,
} as const;

/** How the window's takings split across payment methods. */
export function PaymentMethodPie({
  data,
  currency,
}: {
  data: PaymentMethodSalesRow[];
  currency: string;
}) {
  const points = data
    .filter((row) => Number(row.amount) > 0)
    .map((row) => ({ name: row.name, value: Number(row.amount) }));

  if (points.length === 0) return <ChartEmpty />;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={points}
          dataKey="value"
          nameKey="name"
          innerRadius={58}
          outerRadius={92}
          paddingAngle={2}
        >
          {points.map((point, index) => (
            <Cell key={point.name} fill={`var(--chart-${(index % 5) + 1})`} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: unknown) => formatMoney(Number(value), currency)}
          contentStyle={TOOLTIP_STYLE}
        />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
