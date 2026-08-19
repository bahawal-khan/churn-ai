import { apiRequest } from "./client";
import type { FeatureSchemaField } from "./types";

export type Algorithm = "logistic_regression" | "random_forest" | "gradient_boosting" | "ann";

export interface MetricSummary {
  threshold: number;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  pr_auc: number;
}

export interface RiskThresholds {
  low_max: number;
  medium_max: number;
}

/** Merges the two shapes `GET /api/models` returns (`backend/services/
 * model_registry.py::list_model_summaries` for the filesystem-based
 * baseline + `list_org_model_summaries` for DB-backed company models) —
 * `model_id` is a string for the former, a number for the latter; active
 * state is `selected_as_recommended_production_model` vs `is_active`. */
export interface ModelSummary {
  model_id: string | number;
  algorithm: Algorithm;
  model_type: "baseline_global" | "company_specific" | null;
  version: number | null;
  created_at: string;
  trained_on_dataset?: string;
  trained_on_dataset_id?: number;
  train_row_count?: number;
  decision_threshold: number | null;
  risk_thresholds: RiskThresholds | null;
  selected_as_recommended_production_model?: boolean;
  is_active?: boolean;
  validation_metrics_summary: MetricSummary | null;
  test_metrics_summary: MetricSummary | null;
}

export function isModelActive(model: ModelSummary): boolean {
  return Boolean(model.is_active ?? model.selected_as_recommended_production_model);
}

export interface FullMetricSuite extends MetricSummary {
  confusion_matrix: number[][];
  classification_report: Record<string, unknown>;
}

export interface GlobalShapFeature {
  feature: string;
  mean_abs_shap: number;
  mean_signed_shap: number;
  rank: number;
}

export interface GlobalShap {
  model_id: string | number;
  algorithm: Algorithm;
  explainer_type: string;
  computed_at: string;
  sample_size: number;
  base_value: number;
  additivity_space: string;
  feature_importance: GlobalShapFeature[];
  disclaimer: string;
}

export interface ModelDetail {
  metadata: {
    model_id: string | number;
    algorithm: Algorithm;
    model_type: string | null;
    version: number;
    feature_schema: FeatureSchemaField[];
    decision_threshold: number;
    risk_thresholds: RiskThresholds;
    trained_on_dataset?: string;
    trained_on_dataset_id?: number;
    training_job_id?: number | null;
    is_active?: boolean;
    selected_as_recommended_production_model?: boolean;
    created_at: string;
    [key: string]: unknown;
  };
  metrics: { validation: FullMetricSuite; test: FullMetricSuite | null } | null;
  global_shap: GlobalShap | null;
}

export const modelsApi = {
  list: () => apiRequest<ModelSummary[]>("/api/models"),
  get: (modelId: string | number) => apiRequest<ModelDetail>(`/api/models/${modelId}`),
  activate: (modelId: number) =>
    apiRequest<{ id: number; is_active: boolean }>(`/api/models/${modelId}/activate`, { method: "POST" }),
  deactivate: (modelId: number) =>
    apiRequest<{ id: number; is_active: boolean }>(`/api/models/${modelId}/deactivate`, { method: "POST" }),
};

/** No single endpoint returns "the active model's feature schema" — this
 * mirrors `backend/services/model_registry.py::get_active_bundle_for_org`'s
 * resolution order client-side: org's active company model, else the
 * baseline marked `selected_as_recommended_production_model`. Used to
 * generate `PredictionForm` fields from the model actually serving
 * predictions right now (`docs/FRONTEND_SPEC.md` §12.1). */
export async function getActiveModelDetail(): Promise<ModelDetail | null> {
  const summaries = await modelsApi.list();
  const active = summaries.find((m) => isModelActive(m));
  if (!active) return null;
  return modelsApi.get(active.model_id);
}
