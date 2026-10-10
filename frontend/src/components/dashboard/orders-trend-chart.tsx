"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ChartEmpty } from "@/components/reports/chart-card";
import type { TrendPoint } from "@/lib/api/dashboard";

const TOOLTIP_STYLE = {
  background: "var(--card)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  fontSize: 12,
} as const;

/** Sales volume: the number of orders each day in the window. */
export function OrdersTrendChart({ data }: { data: TrendPoint[] }) {
  if (data.length === 0) return <ChartEmpty />;

  const points = data.map((point) => ({ day: point.day.slice(5), orders: point.orders }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="day"
          tickLine={false}
          axisLine={false}
          fontSize={12}
          stroke="var(--muted-foreground)"
        />
        <YAxis
          allowDecimals={false}
          tickLine={false}
          axisLine={false}
          fontSize={12}
          width={40}
          stroke="var(--muted-foreground)"
        />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Bar dataKey="orders" name="Orders" fill="var(--chart-2)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
