"use client";

import useSWR from "swr";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { SegmentBreakdownChart } from "@/components/dashboard/SegmentBreakdownChart";
import { TopDriversBarList } from "@/components/dashboard/TopDriversBarList";
import { MetricsTable } from "@/components/models/MetricsTable";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { ChartSkeleton } from "@/components/ui/Skeleton";
import { analyticsApi } from "@/lib/api/analytics";
import { isModelActive, modelsApi } from "@/lib/api/models";
import { titleCase } from "@/lib/utils";

const SEGMENT_LABELS: Record<string, string> = {
  Contract: "Risk by Contract Type",
  "Senior Citizen": "Risk by Senior Citizen Status",
  Dependents: "Risk by Dependents",
};

export default function AnalyticsPage() {
  const drivers = useSWR("analytics-top-drivers", () => analyticsApi.topDrivers());
  const segments = useSWR("analytics-segments", () => analyticsApi.segments());
  const models = useSWR("analytics-models", () => modelsApi.list());

  const companyModels = models.data?.filter((m) => m.model_type === "company_specific") ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Analytics</h1>
        <p className="text-sm text-text-muted">Deeper breakdowns of churn drivers, segments, and model performance.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Top Churn Drivers</CardTitle>
        </CardHeader>
        {drivers.error ? (
          <ErrorState error={drivers.error} onRetry={() => drivers.mutate()} />
        ) : !drivers.data ? (
          <ChartSkeleton className="h-48" />
        ) : !drivers.data.available || !drivers.data.feature_importance?.length ? (
          <EmptyState title="No driver data yet" description="Available once the active model has SHAP data." />
        ) : (
          <TopDriversBarList features={drivers.data.feature_importance} />
        )}
      </Card>

      {segments.error ? (
        <ErrorState error={segments.error} onRetry={() => segments.mutate()} />
      ) : !segments.data ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <ChartSkeleton className="h-56" />
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {Object.entries(segments.data.segments).map(([field, breakdown]) => (
            <Card key={field}>
              <CardHeader>
                <CardTitle>{SEGMENT_LABELS[field] ?? `Risk by ${titleCase(field)}`}</CardTitle>
              </CardHeader>
              {Object.keys(breakdown).length === 0 ? (
                <EmptyState title="No data yet" description="Available once customers have been scored." />
              ) : (
                <SegmentBreakdownChart breakdown={breakdown} />
              )}
            </Card>
          ))}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Model Comparison</CardTitle>
        </CardHeader>
        {models.error ? (
          <ErrorState error={models.error} onRetry={() => models.mutate()} />
        ) : !models.data ? (
          <ChartSkeleton className="h-40" />
        ) : companyModels.length === 0 ? (
          <EmptyState
            title="No company-specific models yet"
            description="Train more than one model on your own data to compare performance here."
            actionLabel="Train a model"
            actionHref="/train"
          />
        ) : (
          <div className="flex flex-col gap-6">
            {companyModels.map((model) => (
              <div key={model.model_id}>
                <div className="mb-2 flex items-center gap-2">
                  <p className="text-sm font-semibold text-text-primary">
                    {titleCase(model.algorithm)} v{model.version}
                  </p>
                  {isModelActive(model) && <Badge tone="success">Active</Badge>}
                </div>
                <MetricsTable validation={model.validation_metrics_summary} test={model.test_metrics_summary} />
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
