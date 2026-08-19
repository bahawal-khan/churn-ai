/** Shared envelope/pagination shapes (`docs/BACKEND_SPEC.md` §7, `docs/API.md`
 * cross-cutting notes). Every backend response is one of these two shapes. */

export interface ApiSuccessEnvelope<T> {
  data: T;
  request_id: string | null;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

export interface ApiErrorEnvelope {
  error: ApiErrorBody;
  request_id: string | null;
}

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: Pagination;
}

export type RiskLevel = "low" | "medium" | "high";

export interface FeatureSchemaField {
  name: string;
  dtype: "numeric" | "categorical";
  categories?: string[];
}
