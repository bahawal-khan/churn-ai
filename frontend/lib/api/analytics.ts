import { apiRequest } from "./client";
import type { GlobalShap } from "./models";
import type { RiskLevel } from "./types";

export interface ActiveModelStatus {
  available: boolean;
  model_id?: number | string | null;
  algorithm?: string | null;
  model_type?: string | null;
  version?: number;
  is_baseline?: boolean;
}

/** `backend/services/analytics_service.py::dashboard_summary`: rate/average
 * fields are `null` (not `0` or a fabricated number) until at least one
 * customer has been scored — the empty state renders on `null`, never a
 * plausible-looking placeholder (`docs/PROJECT_SPEC.md` binding rule). */
export interface DashboardSummary {
  total_customers: number;
  scored_customers: number;
  at_risk_customers: number;
  high_risk_customers: number;
  predicted_churn_rate: number | null;
  avg_churn_probability: number | null;
  active_model: ActiveModelStatus;
}

export interface RiskDistribution {
  counts: Record<RiskLevel, number>;
  scored_customers: number;
}

export interface ChurnTrendPoint {
  date: string;
  prediction_count: number;
  predicted_churn_rate: number;
  avg_churn_probability: number;
}

export interface ChurnTrend {
  points: ChurnTrendPoint[];
}

export interface TopDrivers {
  available: boolean;
  feature_importance?: GlobalShap["feature_importance"];
  disclaimer?: string;
}

export type SegmentBreakdown = Record<string, Record<RiskLevel, number>>;

export interface Segments {
  segments: Record<string, SegmentBreakdown>;
}

export const analyticsApi = {
  dashboard: () => apiRequest<DashboardSummary>("/api/analytics/dashboard"),
  riskDistribution: () => apiRequest<RiskDistribution>("/api/analytics/risk-distribution"),
  churnTrend: () => apiRequest<ChurnTrend>("/api/analytics/churn-trend"),
  topDrivers: () => apiRequest<TopDrivers>("/api/analytics/top-drivers"),
  segments: () => apiRequest<Segments>("/api/analytics/segments"),
};
