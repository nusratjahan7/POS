"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { FinancialReport } from "@/lib/api/reports";
import { formatMoney } from "@/lib/format";

/** Revenue, cost, expenses and the two profit lines side by side. */
export function FinancialBarChart({
  report,
  currency,
}: {
  report: FinancialReport;
  currency: string;
}) {
  const points = [
    { name: "Revenue", value: Number(report.revenue), fill: "var(--chart-1)" },
    { name: "Cost", value: Number(report.cost), fill: "var(--chart-3)" },
    { name: "Expenses", value: Number(report.expenses), fill: "var(--chart-5)" },
    { name: "Gross profit", value: Number(report.gross_profit), fill: "var(--chart-2)" },
    { name: "Net profit", value: Number(report.net_profit), fill: "var(--chart-4)" },
  ];

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="name"
          tickLine={false}
          axisLine={false}
          fontSize={12}
          stroke="var(--muted-foreground)"
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          fontSize={12}
          width={72}
          stroke="var(--muted-foreground)"
        />
        <Tooltip
          formatter={(value: unknown) => formatMoney(Number(value), currency)}
          contentStyle={{
            background: "var(--card)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {points.map((point) => (
            <Cell key={point.name} fill={point.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
