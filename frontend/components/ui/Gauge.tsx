import { cn } from "@/lib/utils";
import { formatPercent } from "@/lib/utils";

/** Semi-circular probability gauge for `PredictionForm` results
 * (`docs/FRONTEND_SPEC.md` §12.1). Color follows the risk-level palette so
 * the gauge reinforces, rather than duplicates a separate scale from,
 * `RiskBadge`. */
export function Gauge({
  value,
  riskColorVar,
  label,
  size = 160,
}: {
  value: number;
  riskColorVar: string;
  label?: string;
  size?: number;
}) {
  const clamped = Math.max(0, Math.min(1, value));
  const radius = size / 2 - 10;
  const circumference = Math.PI * radius;
  const offset = circumference * (1 - clamped);

  return (
    <div className="flex flex-col items-center" role="img" aria-label={`Churn probability ${formatPercent(value)}`}>
      <svg width={size} height={size / 2 + 12} viewBox={`0 0 ${size} ${size / 2 + 12}`}>
        <path
          d={`M 10 ${size / 2} A ${radius} ${radius} 0 0 1 ${size - 10} ${size / 2}`}
          fill="none"
          stroke="var(--border-subtle)"
          strokeWidth={10}
          strokeLinecap="round"
        />
        <path
          d={`M 10 ${size / 2} A ${radius} ${radius} 0 0 1 ${size - 10} ${size / 2}`}
          fill="none"
          stroke={riskColorVar}
          strokeWidth={10}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-[stroke-dashoffset] duration-500 ease-out"
        />
        <text
          x={size / 2}
          y={size / 2 - 6}
          textAnchor="middle"
          className={cn("fill-text-primary text-2xl font-bold")}
        >
          {formatPercent(value, 0)}
        </text>
      </svg>
      {label && <span className="text-xs text-text-muted">{label}</span>}
    </div>
  );
}
