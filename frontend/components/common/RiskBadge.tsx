import { Badge } from "@/components/ui/Badge";
import type { RiskLevel } from "@/lib/api/types";
import { cn } from "@/lib/utils";

/** Risk-level color coding always paired with a text label (never color
 * alone, `docs/FRONTEND_SPEC.md` §22 colorblind-safe requirement). */
const RISK_META: Record<RiskLevel, { label: string; tone: "success" | "warning" | "danger"; icon: string }> = {
  low: { label: "Low Risk", tone: "success", icon: "●" },
  medium: { label: "Medium Risk", tone: "warning", icon: "▲" },
  high: { label: "High Risk", tone: "danger", icon: "■" },
};

export function RiskBadge({ level, className }: { level: RiskLevel | null; className?: string }) {
  if (!level) {
    return (
      <Badge tone="neutral" className={className}>
        Unscored
      </Badge>
    );
  }
  const meta = RISK_META[level];
  return (
    <Badge tone={meta.tone} className={cn("font-semibold", className)}>
      <span aria-hidden="true">{meta.icon}</span>
      {meta.label}
    </Badge>
  );
}

export function riskLevelLabel(level: RiskLevel | null): string {
  return level ? RISK_META[level].label : "Unscored";
}
