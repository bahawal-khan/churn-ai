"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip as RechartsTooltip } from "recharts";

import type { RiskLevel } from "@/lib/api/types";
import { formatNumber } from "@/lib/utils";

const RISK_COLORS: Record<RiskLevel, string> = {
  low: "var(--risk-low)",
  medium: "var(--risk-medium)",
  high: "var(--risk-high)",
};

const RISK_LABELS: Record<RiskLevel, string> = { low: "Low Risk", medium: "Medium Risk", high: "High Risk" };

export function RiskDonutChart({ counts, total }: { counts: Record<RiskLevel, number>; total: number }) {
  const data = (["high", "medium", "low"] as RiskLevel[]).map((level) => ({
    name: RISK_LABELS[level],
    value: counts[level],
    level,
  }));

  return (
    // Always stacked (never side-by-side): this chart only ever renders in
    // a narrow dashboard column (`app/(app)/dashboard/page.tsx`'s 1-of-3
    // grid split), and a viewport-width breakpoint like `sm:flex-row` can't
    // tell that the *column* is narrow even on a wide screen — it forced
    // the donut and legend onto one row with too little space, which is
    // what pushed the percentage values past the card edge.
    <div className="flex w-full flex-col items-center gap-4">
      <div className="relative h-52 w-52 shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={62} outerRadius={90} paddingAngle={2}>
              {data.map((entry) => (
                <Cell key={entry.level} fill={RISK_COLORS[entry.level]} />
              ))}
            </Pie>
            <RechartsTooltip
              contentStyle={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-text-primary">{formatNumber(total)}</span>
          <span className="text-xs text-text-muted">Total</span>
        </div>
      </div>
      <ul className="flex w-full max-w-xs flex-col gap-2 text-sm">
        {data.map((entry) => (
          // `min-w-0` on the row and its label span overrides the flex
          // default of `min-width: auto` (which refuses to shrink below
          // content width) so a long label truncates instead of pushing
          // the percentage — marked `shrink-0` — off the edge of the card.
          <li key={entry.level} className="flex min-w-0 items-center justify-between gap-3">
            <span className="flex min-w-0 items-center gap-2 text-text-primary">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: RISK_COLORS[entry.level] }}
                aria-hidden="true"
              />
              <span className="truncate">{entry.name}</span>
            </span>
            <span className="shrink-0 tabular-nums text-text-muted">
              {formatNumber(entry.value)} ({total ? ((entry.value / total) * 100).toFixed(1) : "0.0"}%)
            </span>
          </li>
        ))}
      </ul>
      {/* Screen-reader table-equivalent (`docs/FRONTEND_SPEC.md` §22). */}
      <table className="sr-only">
        <caption>Churn risk distribution</caption>
        <tbody>
          {data.map((entry) => (
            <tr key={entry.level}>
              <th scope="row">{entry.name}</th>
              <td>{entry.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
