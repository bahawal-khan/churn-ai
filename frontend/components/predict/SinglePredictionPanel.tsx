"use client";

import { useState } from "react";
import useSWR from "swr";

import { RiskBadge } from "@/components/common/RiskBadge";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Gauge } from "@/components/ui/Gauge";
import { ChartSkeleton } from "@/components/ui/Skeleton";
import { PredictionForm } from "@/components/predict/PredictionForm";
import { ShapForcePlot } from "@/components/predict/ShapForcePlot";
import { ApiError } from "@/lib/api/client";
import { getActiveModelDetail } from "@/lib/api/models";
import { predictionsApi, type SinglePredictionResult } from "@/lib/api/predictions";
import type { RiskLevel } from "@/lib/api/types";
import { titleCase } from "@/lib/utils";

const RISK_COLOR_VAR: Record<RiskLevel, string> = {
  low: "var(--risk-low)",
  medium: "var(--risk-medium)",
  high: "var(--risk-high)",
};

export function SinglePredictionPanel() {
  const activeModel = useSWR("predict-active-model", () => getActiveModelDetail());
  const [result, setResult] = useState<SinglePredictionResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<ApiError | null>(null);

  async function handleSubmit(customerData: Record<string, unknown>) {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await predictionsApi.predictSingle(customerData);
      setResult(res);
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err : null);
      setResult(null);
    } finally {
      setSubmitting(false);
    }
  }

  if (activeModel.error) return <ErrorState error={activeModel.error} onRetry={() => activeModel.mutate()} />;
  if (!activeModel.data && !activeModel.isLoading) {
    return (
      <EmptyState
        title="No active model available"
        description="Train or activate a model before running predictions."
        actionLabel="Manage models"
        actionHref="/models"
      />
    );
  }
  if (!activeModel.data) return <ChartSkeleton className="h-64" />;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Customer Details</CardTitle>
        </CardHeader>
        <PredictionForm
          fields={activeModel.data.metadata.feature_schema}
          onSubmit={handleSubmit}
          submitting={submitting}
          submitError={submitError}
        />
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Prediction Result</CardTitle>
        </CardHeader>
        {!result ? (
          <p className="text-sm text-text-muted">Fill in the form and submit to see a prediction.</p>
        ) : (
          <div className="flex flex-col items-center gap-4">
            <Gauge value={result.churn_probability} riskColorVar={RISK_COLOR_VAR[result.risk_level]} label="Churn probability" />
            <RiskBadge level={result.risk_level} />
            <p className="text-xs text-text-muted">
              Predicted with {titleCase(result.algorithm)} (decision threshold {(result.decision_threshold * 100).toFixed(0)}%)
            </p>
            <div className="w-full border-t border-border-subtle pt-4">
              <p className="mb-2 text-sm font-semibold text-text-primary">Top Reasons</p>
              <ShapForcePlot explanation={result.explanation} />
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
