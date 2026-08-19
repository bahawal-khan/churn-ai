import { apiRequest } from "./client";
import type { PaginatedResponse } from "./types";

export type TrainingJobStatus =
  | "queued"
  | "validating"
  | "preprocessing"
  | "training"
  | "evaluating"
  | "completed"
  | "failed";

export interface TrainingJob {
  id: number;
  dataset_id: number;
  status: TrainingJobStatus;
  status_message: string | null;
  resulting_model_id: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export const trainingApi = {
  start: (datasetId: number, targetColumn: string) =>
    apiRequest<TrainingJob>("/api/training/jobs", {
      method: "POST",
      json: { dataset_id: datasetId, target_column: targetColumn },
    }),
  get: (jobId: number) => apiRequest<TrainingJob>(`/api/training/jobs/${jobId}`),
  list: (page = 1, pageSize = 20) =>
    apiRequest<PaginatedResponse<TrainingJob>>("/api/training/jobs", { query: { page, page_size: pageSize } }),
};

export const TERMINAL_TRAINING_STATUSES: TrainingJobStatus[] = ["completed", "failed"];
