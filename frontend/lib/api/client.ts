import type { ApiErrorBody, ApiErrorEnvelope, ApiSuccessEnvelope } from "./types";

/** Thrown for every non-2xx response; carries the parsed error envelope
 * (`docs/BACKEND_SPEC.md` §7) so callers can branch on `code` (e.g.
 * `SCHEMA_MISMATCH`, `TRAINING_LABELS_REQUIRED`) instead of parsing
 * `message` text. */
export class ApiError extends Error {
  code: string;
  details: Record<string, unknown>;
  status: number;
  requestId: string | null;

  constructor(body: ApiErrorBody, status: number, requestId: string | null) {
    super(body.message);
    this.name = "ApiError";
    this.code = body.code;
    this.details = body.details ?? {};
    this.status = status;
    this.requestId = requestId;
  }
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE" | "PUT";
  json?: unknown;
  formData?: FormData;
  query?: Record<string, string | number | boolean | undefined | null>;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(path, "http://internal.local");
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.pathname + url.search;
}

/** No component calls `fetch` directly (`docs/FRONTEND_SPEC.md` §1) — every
 * resource module in `lib/api/*.ts` routes through this. Relative URLs only:
 * the Next.js dev proxy (`next.config.js` `rewrites()`) forwards `/api/*` to
 * the real Flask backend same-origin, so cookies work with no CORS setup. */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", json, formData, query, signal } = options;

  const init: RequestInit = {
    method,
    credentials: "include",
    signal,
  };

  if (formData) {
    init.body = formData;
  } else if (json !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(json);
  }

  const response = await fetch(buildUrl(path, query), init);

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const errorPayload = payload as ApiErrorEnvelope | null;
    if (errorPayload && errorPayload.error) {
      throw new ApiError(errorPayload.error, response.status, errorPayload.request_id ?? null);
    }
    throw new ApiError(
      { code: "NETWORK_ERROR", message: `Request failed with status ${response.status}.`, details: {} },
      response.status,
      null
    );
  }

  const successPayload = payload as ApiSuccessEnvelope<T>;
  return successPayload.data;
}

/** XHR-based upload (not `fetch`, which has no upload-progress event) so
 * `UploadDropzone` can show a real progress indicator during large-CSV
 * uploads (`docs/FRONTEND_SPEC.md` §10) — still routed through this single
 * module rather than a component touching a raw browser upload API. */
export function apiUpload<T>(
  path: string,
  formData: FormData,
  onProgress?: (fraction: number) => void
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", path);
    xhr.withCredentials = true;

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(event.loaded / event.total);
      }
    };

    xhr.onload = () => {
      let payload: unknown = null;
      try {
        payload = JSON.parse(xhr.responseText);
      } catch {
        // non-JSON response falls through to the generic error below
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve((payload as ApiSuccessEnvelope<T>).data);
        return;
      }
      const errorPayload = payload as ApiErrorEnvelope | null;
      if (errorPayload?.error) {
        reject(new ApiError(errorPayload.error, xhr.status, errorPayload.request_id ?? null));
      } else {
        reject(
          new ApiError(
            { code: "NETWORK_ERROR", message: `Request failed with status ${xhr.status}.`, details: {} },
            xhr.status,
            null
          )
        );
      }
    };

    xhr.onerror = () => {
      reject(new ApiError({ code: "NETWORK_ERROR", message: "Network request failed.", details: {} }, 0, null));
    };

    xhr.send(formData);
  });
}

export async function apiRequestBlob(path: string, options: RequestOptions = {}): Promise<Blob> {
  const { method = "GET", query, signal } = options;
  const response = await fetch(buildUrl(path, query), { method, credentials: "include", signal });
  if (!response.ok) {
    let payload: ApiErrorEnvelope | null = null;
    try {
      payload = await response.json();
    } catch {
      // non-JSON error body; fall through to generic error below
    }
    if (payload?.error) {
      throw new ApiError(payload.error, response.status, payload.request_id ?? null);
    }
    throw new ApiError(
      { code: "NETWORK_ERROR", message: `Request failed with status ${response.status}.`, details: {} },
      response.status,
      null
    );
  }
  return response.blob();
}
