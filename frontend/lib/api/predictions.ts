import { apiRequest, apiRequestBlob, apiUpload } from "./client";
import type { DataQualityReport } from "./datasets";
import type { Algorithm } from "./models";
import type { PaginatedResponse, RiskLevel } from "./types";

export interface ShapTopFactor {
  feature: string;
  shap_value: number;
  direction: "increases_risk" | "decreases_risk" | "neutral";
}

export interface LocalExplanation {
  model_id?: string | number;
  algorithm?: Algorithm;
  model_output?: number;
  base_value: number;
  shap_values: Record<string, number>;
  top_factors: ShapTopFactor[];
  additivity_check_passed?: boolean;
  disclaimer?: string;
}

export interface SinglePredictionResult {
  prediction_id: number;
  customer_id: string | null;
  model_id: string;
  algorithm: Algorithm;
  decision_threshold: number;
  churn_probability: number;
  predicted_class: number;
  risk_level: RiskLevel;
  explanation: LocalExplanation;
}

export interface BatchPredictionSummary {
  batch_job_id: string;
  model_id: string;
  algorithm: Algorithm;
  id_column: string | null;
  total_rows: number;
  scored_rows: number;
  failed_rows: number;
  predicted_churners: number;
  risk_level_counts: Record<RiskLevel, number>;
}

export interface BatchPredictionRow {
  [column: string]: unknown;
  churn_probability: number | null;
  predicted_class: number | null;
  risk_level: RiskLevel | null;
  prediction_error: string | null;
}

export interface BatchPredictionResult {
  batch_job_id: string;
  dataset_id: number;
  summary: BatchPredictionSummary;
  quality_report: DataQualityReport;
  results: BatchPredictionRow[];
}

export interface BatchStatusResult {
  batch_job_id: string;
  status: "completed";
  scored_rows: number;
  predicted_churners: number;
  risk_level_counts: Record<RiskLevel, number>;
  results: Array<{
    prediction_id: number;
    customer_id: number | null;
    churn_probability: number;
    predicted_class: number;
    risk_level: RiskLevel;
    [field: string]: unknown;
  }>;
}

export interface PredictionHistoryRow {
  id: number;
  model_id: number;
  prediction_type: "single" | "batch";
  customer_id: number | null;
  churn_probability: number;
  predicted_class: number;
  risk_level: RiskLevel;
  batch_job_id: string | null;
  created_at: string;
}

export const predictionsApi = {
  predictSingle: (customerData: Record<string, unknown>, customerId?: string) =>
    apiRequest<SinglePredictionResult>("/api/predictions/single", {
      method: "POST",
      json: { customer_data: customerData, customer_id: customerId },
    }),
  predictBatch: (file: File, onProgress?: (fraction: number) => void) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiUpload<BatchPredictionResult>("/api/predictions/batch", formData, onProgress);
  },
  getBatchStatus: (batchJobId: string) => apiRequest<BatchStatusResult>(`/api/predictions/batch/${batchJobId}`),
  downloadBatchResults: (batchJobId: string) => apiRequestBlob(`/api/predictions/batch/${batchJobId}/download`),
  history: (page = 1, pageSize = 20, riskLevel?: RiskLevel) =>
    apiRequest<PaginatedResponse<PredictionHistoryRow>>("/api/predictions", {
      query: { page, page_size: pageSize, risk_level: riskLevel },
    }),
};
