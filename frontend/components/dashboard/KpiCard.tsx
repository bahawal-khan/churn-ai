import { Card } from "@/components/ui/Card";
import { Tooltip } from "@/components/ui/Tooltip";
import { cn } from "@/lib/utils";

export function KpiCard({
  label,
  value,
  tone = "default",
  tooltip,
  icon,
}: {
  label: string;
  value: string;
  tone?: "default" | "accent" | "warning" | "danger" | "success";
  tooltip?: string;
  icon?: React.ReactNode;
}) {
  const toneClass =
    tone === "accent"
      ? "text-accent-primary"
      : tone === "warning"
        ? "text-risk-medium"
        : tone === "danger"
          ? "text-risk-high"
          : tone === "success"
            ? "text-risk-low"
            : "text-text-primary";

  return (
    <Card className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <p className="truncate text-xs font-medium text-text-muted">
          {tooltip ? <Tooltip content={tooltip}>{label}</Tooltip> : label}
        </p>
        <p className={cn("mt-1 text-kpi-sm sm:text-kpi", toneClass)}>{value}</p>
      </div>
      {icon && <div className={cn("shrink-0", toneClass)}>{icon}</div>}
    </Card>
  );
}
