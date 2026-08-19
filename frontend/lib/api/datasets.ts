import { apiRequest, apiUpload } from "./client";
import type { PaginatedResponse } from "./types";

export interface DataQualityCheck {
  name: string;
  status: "pass" | "warn" | "fail";
  detail: Record<string, unknown>;
}

export interface DataQualityReport {
  checks: DataQualityCheck[];
  [key: string]: unknown;
}

export interface ColumnSchemaField {
  name: string;
  dtype: "numeric" | "categorical";
}

export interface Dataset {
  id: number;
  organization_id: number | null;
  original_filename: string;
  source_type: "dev_benchmark_ibm" | "dev_synthetic_pakistan" | "dev_synthetic_india" | "company_upload";
  row_count: number;
  column_schema: ColumnSchemaField[];
  column_mapping: Record<string, string> | null;
  data_quality_report: DataQualityReport;
  has_target_column: boolean;
  target_column_name: string | null;
  created_at: string;
}

export interface DatasetUploadResult {
  dataset: Dataset;
  quality_report: DataQualityReport;
  preview: Record<string, unknown>[];
}

export const datasetsApi = {
  upload: (file: File, targetColumn?: string, onProgress?: (fraction: number) => void) => {
    const formData = new FormData();
    formData.append("file", file);
    if (targetColumn) formData.append("target_column", targetColumn);
    return apiUpload<DatasetUploadResult>("/api/datasets", formData, onProgress);
  },
  list: (page = 1, pageSize = 20) =>
    apiRequest<PaginatedResponse<Dataset>>("/api/datasets", { query: { page, page_size: pageSize } }),
  get: (id: number) => apiRequest<Dataset>(`/api/datasets/${id}`),
  remove: (id: number) => apiRequest<{ deleted: boolean }>(`/api/datasets/${id}`, { method: "DELETE" }),
};
