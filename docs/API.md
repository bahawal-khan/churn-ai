
# ChurnAI — API Specification (API.md)

Companion to `PROJECT_SPEC.md` and `BACKEND_SPEC.md`. All endpoints are prefixed `/api`. All responses use the standard success shape `{ "data": ..., "request_id": "..." }` or the error envelope defined in `BACKEND_SPEC.md §7`. All non-auth, non-health endpoints require a valid session cookie and are scoped to the caller's organization (`DATABASE_SPEC.md §6`).

---

## Auth — `/api/auth`

| Method & Path | Description | Success |
|---|---|---|
| `POST /signup` | `{ email, password, confirm_password, full_name }` → create user + org, issue session | 201, user profile |
| `POST /login` | `{ email, password }` → issue session | 200, user profile |
| `POST /logout` | Revoke current session | 200 |
| `GET /session` | Return current user if session valid, else 401 | 200 / 401 |
| `POST /forgot-password` | `{ email }` → issue reset token (always 200, regardless of whether the email exists, to avoid enumeration) | 200 |
| `POST /reset-password` | `{ token, new_password, confirm_password }` → set new password, revoke existing sessions | 200 |

## Datasets — `/api/datasets`

| Method & Path | Description |
|---|---|
| `POST /` | Multipart upload of a CSV; runs validation + `DataQualityValidator`; returns dataset id, preview rows, schema detection, quality report |
| `GET /` | List datasets for the caller's org (paginated) |
| `GET /:id` | Dataset detail incl. full quality report |
| `DELETE /:id` | Delete a dataset (confirmation required client-side; cascades per FK rules, blocked if a model was trained from it — must be handled per a documented cascade/soft-delete policy pinned in Phase 8) |

## Training — `/api/training`

| Method & Path | Description |
|---|---|
| `POST /jobs` | `{ dataset_id, target_column }` → validates target column exists & is binary, creates a `training_jobs` row (`queued`), returns job id. Returns `422 TRAINING_LABELS_REQUIRED` if no valid target is available |
| `GET /jobs/:id` | Poll job status (`queued`→...→`completed`/`failed`), includes `status_message` and, once completed, the resulting `model_id` |
| `GET /jobs` | List training job history for the org |

## Models — `/api/models`

| Method & Path | Description |
|---|---|
| `GET /` | List models available to the org (the shared baseline + the org's company-specific versions) with metrics summary |
| `GET /:id` | Full model detail: metrics, metadata, global SHAP summary |
| `POST /:id/activate` | Set as the org's active company-specific model (deactivates the previous one) |
| `POST /:id/deactivate` | Deactivate (falls back to the baseline model for predictions) |

## Predictions — `/api/predictions`

| Method & Path | Description |
|---|---|
| `POST /single` | `{ customer_data: {...schema fields...} }` → validated against the active model's stored `feature_schema` (`ML_SPEC.md §14`) before inference; returns `422 SCHEMA_MISMATCH` if required fields are missing/mismatched → otherwise churn probability, predicted class, risk level, local SHAP explanation, using the org's active model (falls back to baseline if none active) |
| `POST /batch` | Multipart CSV upload → ingested through the same dataset pipeline as training uploads (creates a `datasets` row, `source_type = 'company_upload'`, and per-row `customers` records — matched by `external_customer_id` when it identifies an existing org customer, otherwise created — so every predicted row is linked to a stored customer and appears in Customer List/Detail) → validated via `DataQualityValidator` (target column not required) and against the active model's `feature_schema` per `PROJECT_SPEC.md §16.1` → synchronous result for small files or a `batch_job_id` to poll for larger files → summary counts + downloadable results |
| `GET /batch/:batch_job_id` | Poll batch job status / retrieve summary once complete |
| `GET /batch/:batch_job_id/download` | Stream the results CSV (original columns + `churn_probability`, `predicted_class`, `risk_level`) |
| `GET /` | Prediction history (paginated, filterable by risk level / date range / customer) |

## Customers — `/api/customers`

| Method & Path | Description |
|---|---|
| `GET /` | List customers for the org (search, filter by risk level, sort, paginate) |
| `GET /:id` | Customer detail: stored feature data + full prediction history for that customer |

## Analytics — `/api/analytics`

| Method & Path | Description |
|---|---|
| `GET /dashboard` | KPI summary (total customers, at-risk count, predicted churn rate, high-risk count, avg churn probability), computed from real stored data only |
| `GET /risk-distribution` | Counts per risk level for the donut chart |
| `GET /churn-trend` | Time-series of predicted churn rate, computed from stored prediction history |
| `GET /top-drivers` | Global SHAP summary for the active model |
| `GET /segments` | Risk breakdown by a defined set of segment cuts (contract type, senior citizen, dependents, etc.) |

## Reports — `/api/reports`

| Method & Path | Description |
|---|---|
| `POST /generate` | `{ report_type, filters }` → generates an exportable summary (PDF/CSV, format TBD at Phase 10/12 based on the `pdf`/`xlsx` tooling actually wired up) |
| `GET /` | List previously generated reports |
| `GET /:id/download` | Download a generated report |

## Health — `/api/health`

| Method & Path | Description |
|---|---|
| `GET /` | Unauthenticated health check: `{ status, db, version }` |

---

## Cross-Cutting Notes

- **Pagination:** list endpoints accept `?page=&page_size=` and return `{ data: [...], pagination: { page, page_size, total, total_pages } }`.
- **Filtering/sorting:** documented per-endpoint via query params (e.g., `?risk_level=high&sort=-created_at`) once finalized in Phase 8/11 — this document is the contract skeleton; exact query-param names are finalized alongside the matching `DataTable` frontend component and recorded here before Phase 11 integration closes.
- **Idempotency:** upload and training-start endpoints are not idempotent by design (each call creates a new dataset/job); the frontend prevents accidental double-submission via disabled-state handling during in-flight requests.
- **Versioning:** all routes are unversioned (`/api/...`) for V1; a `/api/v2/...` prefix is the documented path if a breaking change is needed later.
