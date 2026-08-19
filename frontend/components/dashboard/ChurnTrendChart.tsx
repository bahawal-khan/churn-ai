"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip as RechartsTooltip, XAxis, YAxis } from "recharts";

import type { ChurnTrendPoint } from "@/lib/api/analytics";
import { formatDate, formatPercent } from "@/lib/utils";

export function ChurnTrendChart({ points }: { points: ChurnTrendPoint[] }) {
  const data = points.map((p) => ({ ...p, dateLabel: formatDate(p.date) }));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
          <XAxis dataKey="dateLabel" tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
          <YAxis
            tickFormatter={(v) => `${Math.round(v * 100)}%`}
            tick={{ fontSize: 11, fill: "var(--text-muted)" }}
            width={44}
          />
          <RechartsTooltip
            formatter={(value: number) => formatPercent(value)}
            contentStyle={{
              background: "var(--bg-elevated)",
              border: "1px solid var(--border-subtle)",
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Line
            type="monotone"
            dataKey="predicted_churn_rate"
            name="Predicted churn rate"
            stroke="var(--accent-primary)"
            strokeWidth={2}
            dot={false}
            isAnimationActive
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
