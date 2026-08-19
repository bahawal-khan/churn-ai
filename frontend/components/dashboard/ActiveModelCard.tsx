import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import type { ModelDetail } from "@/lib/api/models";
import { SYNTHETIC_DATA_DISCLAIMER } from "@/lib/siteConfig";
import { formatDate, formatPercent, titleCase } from "@/lib/utils";

export function ActiveModelCard({ model }: { model: ModelDetail }) {
  const isBaseline = model.metadata.model_type === "baseline_global";
  const testAuc = model.metrics?.test?.roc_auc ?? model.metrics?.validation?.roc_auc ?? null;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-text-primary">{titleCase(model.metadata.algorithm)}</p>
          <p className="text-xs text-text-muted">
            v{model.metadata.version} · {isBaseline ? "Shared baseline" : "Company-specific"}
          </p>
        </div>
        <Badge tone="success">Active</Badge>
      </div>
      <dl className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-xs text-text-muted">ROC-AUC</dt>
          <dd className="font-semibold text-text-primary">{testAuc !== null ? testAuc.toFixed(3) : "—"}</dd>
        </div>
        <div>
          <dt className="text-xs text-text-muted">Decision threshold</dt>
          <dd className="font-semibold text-text-primary">{formatPercent(model.metadata.decision_threshold, 0)}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-xs text-text-muted">Trained on</dt>
          <dd className="text-text-primary">{formatDate(model.metadata.created_at)}</dd>
        </div>
      </dl>
      {isBaseline && <p className="text-xs text-text-muted">{SYNTHETIC_DATA_DISCLAIMER}</p>}
      <Link href="/models" className="text-xs font-medium text-accent-primary hover:underline">
        View all models →
      </Link>
    </div>
  );
}
