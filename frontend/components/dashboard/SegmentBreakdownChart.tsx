"use client";

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip as RechartsTooltip, XAxis, YAxis } from "recharts";

import type { SegmentBreakdown } from "@/lib/api/analytics";

/** Risk breakdown by a segment field (contract type / senior citizen /
 * dependents — real schema cuts, `docs/PROJECT_SPEC.md` §19), rendered as a
 * stacked bar chart (spec allows "radar or bar view"; bar reads more
 * clearly for count data across an arbitrary number of category values). */
export function SegmentBreakdownChart({ breakdown }: { breakdown: SegmentBreakdown }) {
  const data = Object.entries(breakdown).map(([value, counts]) => ({
    name: value,
    Low: counts.low,
    Medium: counts.medium,
    High: counts.high,
  }));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
          <YAxis tick={{ fontSize: 11, fill: "var(--text-muted)" }} width={32} allowDecimals={false} />
          <RechartsTooltip
            contentStyle={{
              background: "var(--bg-elevated)",
              border: "1px solid var(--border-subtle)",
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="Low" stackId="risk" fill="var(--risk-low)" />
          <Bar dataKey="Medium" stackId="risk" fill="var(--risk-medium)" />
          <Bar dataKey="High" stackId="risk" fill="var(--risk-high)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
