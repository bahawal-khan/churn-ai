"use client";

import { useParams } from "next/navigation";
import useSWR from "swr";

import { ErrorState } from "@/components/common/ErrorState";
import { TopDriversBarList } from "@/components/dashboard/TopDriversBarList";
import { MetricsTable } from "@/components/models/MetricsTable";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { modelsApi } from "@/lib/api/models";
import { SYNTHETIC_DATA_DISCLAIMER } from "@/lib/siteConfig";
import { formatDate, formatPercent, titleCase } from "@/lib/utils";

export default function ModelDetailPage() {
  const params = useParams<{ id: string }>();
  const detail = useSWR(`model-detail-${params.id}`, () => modelsApi.get(params.id));

  if (detail.error) return <ErrorState error={detail.error} onRetry={() => detail.mutate()} />;
  if (!detail.data) return <TableSkeleton rows={6} columns={2} />;

  const { metadata, metrics, global_shap } = detail.data;
  const isBaseline = metadata.model_type === "baseline_global";

  return (
    <div className="flex flex-col gap-6">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-text-primary">
            {titleCase(metadata.algorithm)} v{metadata.version}
          </h1>
          {(metadata.is_active ?? metadata.selected_as_recommended_production_model) && <Badge tone="success">Active</Badge>}
        </div>
        <p className="text-sm text-text-muted">
          {isBaseline ? "Shared baseline model" : "Company-specific model"} · Trained {formatDate(metadata.created_at)}
        </p>
      </div>

      {isBaseline && (
        <p className="rounded-control bg-accent-primary-soft p-3 text-sm text-text-primary">{SYNTHETIC_DATA_DISCLAIMER}</p>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Metrics</CardTitle>
        </CardHeader>
        {metrics ? (
          <MetricsTable validation={metrics.validation} test={metrics.test} />
        ) : (
          <p className="text-sm text-text-muted">No metrics recorded for this model.</p>
        )}
        <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-xs text-text-muted">Decision Threshold</dt>
            <dd className="font-medium text-text-primary">{formatPercent(metadata.decision_threshold, 0)}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-muted">Low / Medium boundary</dt>
            <dd className="font-medium text-text-primary">{formatPercent(metadata.risk_thresholds?.low_max, 0)}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-muted">Medium / High boundary</dt>
            <dd className="font-medium text-text-primary">{formatPercent(metadata.risk_thresholds?.medium_max, 0)}</dd>
          </div>
        </dl>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Global SHAP Summary</CardTitle>
        </CardHeader>
        {!global_shap || global_shap.feature_importance.length === 0 ? (
          <p className="text-sm text-text-muted">No SHAP summary available for this model.</p>
        ) : (
          <TopDriversBarList features={global_shap.feature_importance} />
        )}
      </Card>
    </div>
  );
}
