import { apiRequest, apiRequestBlob } from "./client";
import type { PaginatedResponse } from "./types";

export type ReportType = "predictions_summary" | "customers_summary";

export interface ReportMetadata {
  id: string;
  report_type: ReportType;
  filters: Record<string, unknown>;
  row_count: number;
  created_at: string;
  created_by_user_id: number | null;
}

export const REPORT_TYPES: { value: ReportType; label: string; description: string }[] = [
  {
    value: "predictions_summary",
    label: "Predictions Summary",
    description: "Every prediction made by your organization, with churn probability and risk level.",
  },
  {
    value: "customers_summary",
    label: "Customers Summary",
    description: "Every stored customer with their latest churn probability and risk level.",
  },
];

export const reportsApi = {
  generate: (reportType: ReportType, filters: Record<string, unknown> = {}) =>
    apiRequest<ReportMetadata>("/api/reports/generate", { method: "POST", json: { report_type: reportType, filters } }),
  list: (page = 1, pageSize = 20) =>
    apiRequest<PaginatedResponse<ReportMetadata>>("/api/reports", { query: { page, page_size: pageSize } }),
  download: (reportId: string) => apiRequestBlob(`/api/reports/${reportId}/download`),
};
