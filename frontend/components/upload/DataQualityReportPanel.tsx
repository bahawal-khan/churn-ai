import { Badge } from "@/components/ui/Badge";
import type { DataQualityReport } from "@/lib/api/datasets";
import { titleCase } from "@/lib/utils";

const STATUS_TONE = { pass: "success", warn: "warning", fail: "danger" } as const;

/** Per-check pass/warn/fail rendering (`docs/FRONTEND_SPEC.md` §10),
 * matching `ml/data_quality/validator.py`'s report shape. */
export function DataQualityReportPanel({ report }: { report: DataQualityReport }) {
  if (!report.checks?.length) {
    return <p className="text-sm text-text-muted">No data quality checks were recorded for this file.</p>;
  }

  return (
    <ul className="flex flex-col divide-y divide-border-subtle rounded-card border border-border-subtle">
      {report.checks.map((check) => (
        <li key={check.name} className="flex flex-col gap-1 p-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-medium text-text-primary">{titleCase(check.name)}</p>
            {Object.keys(check.detail ?? {}).length > 0 && (
              <p className="mt-0.5 text-xs text-text-muted">{summarizeDetail(check.detail)}</p>
            )}
          </div>
          <Badge tone={STATUS_TONE[check.status]} className="self-start">
            {check.status.toUpperCase()}
          </Badge>
        </li>
      ))}
    </ul>
  );
}

function summarizeDetail(detail: Record<string, unknown>): string {
  return Object.entries(detail)
    .map(([key, value]) => `${titleCase(key)}: ${Array.isArray(value) ? value.join(", ") : String(value)}`)
    .join(" · ");
}
