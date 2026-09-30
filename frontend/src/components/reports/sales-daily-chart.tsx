"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ChartEmpty } from "@/components/reports/chart-card";
import type { SalesDailyPoint } from "@/lib/api/reports";
import { formatMoney } from "@/lib/format";

const TOOLTIP_STYLE = {
  background: "var(--card)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  fontSize: 12,
} as const;

/** Revenue over the window, one point per day with sales. */
export function SalesDailyChart({
  data,
  currency,
}: {
  data: SalesDailyPoint[];
  currency: string;
}) {
  if (data.length === 0) return <ChartEmpty />;

  const points = data.map((point) => ({
    day: point.day.slice(5),
    total: Number(point.total),
    orders: point.orders,
  }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="report-sales-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.35} />
            <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="day"
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
          contentStyle={TOOLTIP_STYLE}
        />
        <Area
          type="monotone"
          dataKey="total"
          name="Sales"
          stroke="var(--chart-1)"
          fill="url(#report-sales-fill)"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
