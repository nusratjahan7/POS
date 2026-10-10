"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ChartEmpty } from "@/components/reports/chart-card";
import type { TrendPoint } from "@/lib/api/dashboard";
import { formatMoney } from "@/lib/format";

const TOOLTIP_STYLE = {
  background: "var(--card)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  fontSize: 12,
} as const;

/** Net profit per day: revenue less cost of goods and expenses. */
export function ProfitTrendChart({ data, currency }: { data: TrendPoint[]; currency: string }) {
  if (data.length === 0) return <ChartEmpty />;

  const points = data.map((point) => ({ day: point.day.slice(5), profit: Number(point.profit) }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="dashboard-profit-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--chart-3)" stopOpacity={0.35} />
            <stop offset="100%" stopColor="var(--chart-3)" stopOpacity={0} />
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
        <ReferenceLine y={0} stroke="var(--border)" />
        <Area
          type="monotone"
          dataKey="profit"
          name="Profit"
          stroke="var(--chart-3)"
          fill="url(#dashboard-profit-fill)"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
