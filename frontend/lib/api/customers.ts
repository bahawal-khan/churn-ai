import { apiRequest } from "./client";
import type { ShapTopFactor } from "./predictions";
import type { PaginatedResponse, RiskLevel } from "./types";

export interface Customer {
  id: number;
  organization_id: number;
  dataset_id: number;
  external_customer_id: string | null;
  feature_data: Record<string, unknown>;
  actual_churn_label: boolean | null;
  latest_risk_level: RiskLevel | null;
  created_at: string;
}

export interface CustomerPrediction {
  id: number;
  model_id: number;
  prediction_type: "single" | "batch";
  churn_probability: number;
  predicted_class: boolean;
  risk_level: RiskLevel;
  batch_job_id: string | null;
  created_at: string;
  explanation: {
    shap_values: Record<string, number>;
    base_value: number;
    top_factors: ShapTopFactor[];
  } | null;
}

export interface CustomerDetail {
  customer: Customer;
  predictions: CustomerPrediction[];
}

export const customersApi = {
  list: (params: { page?: number; pageSize?: number; search?: string; riskLevel?: RiskLevel } = {}) =>
    apiRequest<PaginatedResponse<Customer>>("/api/customers", {
      query: {
        page: params.page ?? 1,
        page_size: params.pageSize ?? 20,
        search: params.search,
        risk_level: params.riskLevel,
      },
    }),
  get: (id: number) => apiRequest<CustomerDetail>(`/api/customers/${id}`),
};
