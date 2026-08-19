# ChurnAI — Database Specification (DATABASE_SPEC.md)

Companion to `PROJECT_SPEC.md`, `BACKEND_SPEC.md`, `ML_SPEC.md`, and `API.md`. SQLite for V1, schema designed to migrate to PostgreSQL later with no application-code changes: standard SQL types only, Alembic migrations from the first commit, no SQLite-specific features relied upon.

This document is the single source of truth for every table, relationship, index, and constraint referenced elsewhere in the spec set (e.g., `PROJECT_SPEC.md §16`'s reference to a model's stored `feature_schema`, `BACKEND_SPEC.md §4`'s session/auth tables, `ML_SPEC.md §14`'s model artifact metadata).

---

## 1. Entity-Relationship Overview

```
users ──1:1── organizations ──1:N── datasets ──1:N── customers
   │                              ├──1:N── training_jobs ──1:1── models
   │                              ├──1:N── models (baseline + company-specific versions)
   │                              ├──1:N── predictions ──1:1── explanations
   │                              └──1:N── audit_logs
   └──1:N── sessions
   └──1:N── password_reset_tokens
```

**Tenant model (V1):** one `organization` per `user` (PROJECT_SPEC §49 V1 scope — no multi-user org invites yet). Every tenant-scoped table carries `organization_id` directly, so the isolation rule (§6) is a single-column filter everywhere, not a join through `users`. Modeling `organizations` as its own entity — rather than scoping everything directly to `user_id` — means multi-user organizations are an additive future migration (add a `memberships` join table), not a schema rewrite.

**Global vs. tenant-scoped data:** the shared baseline model (`models.organization_id IS NULL`, PROJECT_SPEC §3.0) and its source datasets (`datasets.source_type IN ('dev_benchmark_ibm','dev_synthetic_pakistan','dev_synthetic_india')`, also `organization_id IS NULL`) are the only rows in the schema not owned by a tenant. Every other row in every tenant-scoped table always has a non-null `organization_id`.

---

## 2. Tables

### 2.1 `users`
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| email | TEXT | NOT NULL, UNIQUE (stored lowercase), indexed |
| password_hash | TEXT | NOT NULL — Argon2 hash, never plaintext |
| full_name | TEXT | NOT NULL |
| organization_id | INTEGER | NOT NULL, FK → `organizations.id` |
| theme_preference | TEXT | NOT NULL, DEFAULT `'dark'`, CHECK IN (`'light'`, `'dark'`) |
| onboarding_completed_at | DATETIME | NULL — set when the guided tour (`FRONTEND_SPEC.md §8`) is finished/skipped |
| created_at | DATETIME | NOT NULL, DEFAULT now |
| updated_at | DATETIME | NOT NULL, DEFAULT now, updated on write |

### 2.2 `organizations`
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| name | TEXT | NOT NULL — defaults to `"{full_name}'s workspace"` at signup |
| created_at | DATETIME | NOT NULL, DEFAULT now |

### 2.3 `sessions`
Backs the cookie-based session mechanism (`BACKEND_SPEC.md §4`).

| Column | Type | Constraints |
|---|---|---|
| id | TEXT | PK — opaque, cryptographically random session id stored in the HttpOnly cookie |
| user_id | INTEGER | NOT NULL, FK → `users.id`, indexed |
| created_at | DATETIME | NOT NULL, DEFAULT now |
| expires_at | DATETIME | NOT NULL, indexed (for expiry sweep) — `created_at + SESSION_TTL_DAYS` (`DEPLOYMENT.md §2`, default 7 days) |
| revoked_at | DATETIME | NULL — set on logout or password reset |
| user_agent | TEXT | NULL — stored for the user's own visibility into active sessions (future Settings feature) |

A session is valid only if `revoked_at IS NULL AND expires_at > now()`. `GET /api/auth/session` (`API.md`) checks exactly this condition.

### 2.4 `password_reset_tokens`
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| user_id | INTEGER | NOT NULL, FK → `users.id`, indexed |
| token_hash | TEXT | NOT NULL — raw token is never stored, only its hash |
| expires_at | DATETIME | NOT NULL — `created_at + PASSWORD_RESET_TOKEN_TTL_MINUTES` (`DEPLOYMENT.md §2`) |
| used_at | DATETIME | NULL — set on successful reset; a used or expired token is rejected |
| created_at | DATETIME | NOT NULL, DEFAULT now |

### 2.5 `datasets`
Represents every uploaded CSV: development/benchmark, synthetic regional, or company production data (`PROJECT_SPEC.md §3.0`).

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| organization_id | INTEGER | NULL for dev/synthetic datasets; NOT NULL FK → `organizations.id` for company uploads; indexed |
| original_filename | TEXT | NOT NULL — display only, never used to build a filesystem path (`BACKEND_SPEC.md §6`) |
| storage_path | TEXT | NOT NULL, UNIQUE — server-generated UUID-based path |
| source_type | TEXT | NOT NULL, CHECK IN (`'dev_benchmark_ibm'`, `'dev_synthetic_pakistan'`, `'dev_synthetic_india'`, `'company_upload'`) |
| row_count | INTEGER | NOT NULL |
| column_schema | JSON | NOT NULL — detected columns + inferred types |
| column_mapping | JSON | NULL — the confirmed upload→schema-contract field mapping from the Preview step (`PROJECT_SPEC.md §16.1`) |
| data_quality_report | JSON | NOT NULL — full report per `ML_SPEC.md §3` |
| has_target_column | BOOLEAN | NOT NULL, DEFAULT `false` |
| target_column_name | TEXT | NULL |
| uploaded_by_user_id | INTEGER | NULL, FK → `users.id` (NULL for system-seeded dev/synthetic datasets) |
| created_at | DATETIME | NOT NULL, DEFAULT now, indexed |

### 2.6 `customers`
Row-level records belonging to a dataset — the entities predictions are made about.

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| organization_id | INTEGER | NOT NULL, FK → `organizations.id`, indexed |
| dataset_id | INTEGER | NOT NULL, FK → `datasets.id`, indexed |
| external_customer_id | TEXT | NULL — as supplied in source data, display only, never trusted as a join key across datasets |
| feature_data | JSON | NOT NULL — the row's values for the schema-contract fields (`ML_SPEC.md §1`) |
| actual_churn_label | BOOLEAN | NULL — historical outcome, if known |
| created_at | DATETIME | NOT NULL, DEFAULT now |

### 2.7 `models`
Every trained model version: the shared baseline and each company-specific version.

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| organization_id | INTEGER | NULL for the shared baseline model; NOT NULL FK → `organizations.id` for company-specific models; indexed |
| model_type | TEXT | NOT NULL, CHECK IN (`'baseline_global'`, `'company_specific'`) |
| algorithm | TEXT | NOT NULL, CHECK IN (`'logistic_regression'`, `'random_forest'`, `'gradient_boosting'`, `'ann'`) |
| version | INTEGER | NOT NULL — increments per `(organization_id, model_type)` |
| artifact_path | TEXT | NOT NULL, UNIQUE — directory per `ML_SPEC.md §14` (`model.*`, `pipeline.joblib`, `metadata.json`, `metrics.json`, `global_shap.json`) |
| feature_schema | JSON | NOT NULL — the exact ordered list of input columns + expected types/categories the fitted pipeline expects; this is what `PROJECT_SPEC.md §16` prediction-time validation checks incoming single/batch requests against, and what `API.md`'s `SCHEMA_MISMATCH` error is raised from |
| metrics | JSON | NOT NULL — full validation + test metric suite (`ML_SPEC.md §12`) |
| decision_threshold | FLOAT | NOT NULL — tuned per `ML_SPEC.md §12` |
| risk_thresholds | JSON | NOT NULL — `{ "low_max": 0.3, "medium_max": 0.6 }` (`PROJECT_SPEC.md §18`) |
| trained_on_dataset_id | INTEGER | NOT NULL, FK → `datasets.id` |
| training_job_id | INTEGER | NULL, FK → `training_jobs.id` — null for the initial baseline model, which is produced by the Phase 1–7 ML pipeline and seeded into this table via a one-off script during Phase 9 (Database & Authentication), before the `training_jobs` workflow exists (no `training_jobs` row is created for it) |
| is_active | BOOLEAN | NOT NULL, DEFAULT `false` |
| created_at | DATETIME | NOT NULL, DEFAULT now, indexed |

**Constraint:** at most one row per `organization_id` may have `model_type = 'company_specific' AND is_active = true` at any time (enforced at the service layer via a transaction that deactivates the previous active model before activating a new one, `API.md`'s `POST /models/:id/activate`; documented here as a business rule since SQLite's partial-unique-index support is limited — enforced again as a real partial unique index once migrated to PostgreSQL, see §8).

### 2.8 `training_jobs`
The state machine backing the company-specific training workflow (`PROJECT_SPEC.md §16`, `BACKEND_SPEC.md §3`).

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| organization_id | INTEGER | NOT NULL, FK → `organizations.id`, indexed |
| dataset_id | INTEGER | NOT NULL, FK → `datasets.id` |
| status | TEXT | NOT NULL, DEFAULT `'queued'`, CHECK IN (`'queued'`, `'validating'`, `'preprocessing'`, `'training'`, `'evaluating'`, `'completed'`, `'failed'`) |
| status_message | TEXT | NULL — human-readable current-step or failure reason |
| resulting_model_id | INTEGER | NULL, FK → `models.id` — set once `status = 'completed'` |
| started_at | DATETIME | NULL |
| completed_at | DATETIME | NULL |
| created_at | DATETIME | NOT NULL, DEFAULT now, indexed |

### 2.9 `predictions`
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| organization_id | INTEGER | NOT NULL, FK → `organizations.id`, indexed |
| model_id | INTEGER | NOT NULL, FK → `models.id` — the exact model version used |
| prediction_type | TEXT | NOT NULL, CHECK IN (`'single'`, `'batch'`) |
| customer_id | INTEGER | NULL, FK → `customers.id` — null only for single/ad-hoc predictions not tied to a stored customer. Batch predictions always populate this: a batch upload is ingested through the same dataset pipeline as training uploads (creating a `datasets` row and per-row `customers` records, or matching existing customers by `external_customer_id`), so every batch-predicted row is linked to a stored customer (`PROJECT_SPEC.md §17`, `API.md`) |
| input_data | JSON | NOT NULL — the exact input feature values used (never inferred after the fact) |
| churn_probability | FLOAT | NOT NULL, CHECK (`churn_probability >= 0 AND churn_probability <= 1`) |
| predicted_class | BOOLEAN | NOT NULL |
| risk_level | TEXT | NOT NULL, CHECK IN (`'low'`, `'medium'`, `'high'`) |
| batch_job_id | TEXT | NULL, indexed — groups rows from one batch upload; corresponds to `API.md`'s `batch_job_id` |
| created_at | DATETIME | NOT NULL, DEFAULT now, indexed |

Every value in this table is written once, at prediction time, from an actual model inference call — nothing in this table is ever backfilled with a placeholder or estimated value (binding rule, `PROJECT_SPEC.md`, top of document).

### 2.10 `explanations`
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| prediction_id | INTEGER | NOT NULL, FK → `predictions.id`, UNIQUE — exactly one local explanation per prediction |
| shap_values | JSON | NOT NULL — per-feature contribution values, actual SHAP library output (`ML_SPEC.md §13`) |
| base_value | FLOAT | NOT NULL — SHAP expected value |
| top_factors | JSON | NOT NULL — ranked top contributing features, precomputed at write time for fast UI rendering (`FRONTEND_SPEC.md`'s SHAP visualization components read this column directly, not `shap_values`, for the summary view) |
| created_at | DATETIME | NOT NULL, DEFAULT now |

### 2.11 `audit_logs`
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| organization_id | INTEGER | NULL (null for pre-auth events like a failed login attempt against an unknown email), FK → `organizations.id`, indexed |
| user_id | INTEGER | NULL, FK → `users.id` |
| event_type | TEXT | NOT NULL, CHECK IN (`'login'`, `'logout'`, `'signup'`, `'password_reset'`, `'dataset_upload'`, `'dataset_delete'`, `'training_started'`, `'training_completed'`, `'training_failed'`, `'model_activated'`, `'model_deactivated'`, `'prediction_made'`) |
| event_details | JSON | NULL |
| created_at | DATETIME | NOT NULL, DEFAULT now, indexed |

---

## 3. Relationships (foreign keys, summarized)

| Table | FK column | References | On delete |
|---|---|---|---|
| `users` | `organization_id` | `organizations.id` | RESTRICT (an org is never deleted while a user references it in V1's one-user-per-org model) |
| `sessions` | `user_id` | `users.id` | CASCADE |
| `password_reset_tokens` | `user_id` | `users.id` | CASCADE |
| `datasets` | `organization_id` | `organizations.id` | CASCADE |
| `datasets` | `uploaded_by_user_id` | `users.id` | SET NULL |
| `customers` | `organization_id` | `organizations.id` | CASCADE |
| `customers` | `dataset_id` | `datasets.id` | CASCADE |
| `models` | `organization_id` | `organizations.id` | CASCADE |
| `models` | `trained_on_dataset_id` | `datasets.id` | RESTRICT (a dataset a model was trained from cannot be hard-deleted while the model still references it — matches `API.md`'s `DELETE /api/datasets/:id` note that this cascade/soft-delete policy is finalized in Phase 8; deletion is blocked with a clear error until the dependent model is deleted or the dataset delete is confirmed as a soft-delete instead) |
| `models` | `training_job_id` | `training_jobs.id` | SET NULL |
| `training_jobs` | `organization_id` | `organizations.id` | CASCADE |
| `training_jobs` | `dataset_id` | `datasets.id` | RESTRICT |
| `training_jobs` | `resulting_model_id` | `models.id` | SET NULL |
| `predictions` | `organization_id` | `organizations.id` | CASCADE |
| `predictions` | `model_id` | `models.id` | RESTRICT (prediction history must always be traceable to the exact model version that produced it — a model is never hard-deleted while predictions reference it; V1 only deactivates models, it does not delete them) |
| `predictions` | `customer_id` | `customers.id` | SET NULL |
| `explanations` | `prediction_id` | `predictions.id` | CASCADE |
| `audit_logs` | `organization_id` | `organizations.id` | SET NULL |
| `audit_logs` | `user_id` | `users.id` | SET NULL |

`PRAGMA foreign_keys = ON` is set once per connection in `db/session.py` (§7, SQLite Implementation Notes) — SQLite does not enforce FKs by default, and this must not be forgotten.

---

## 4. Indexes

Beyond the primary keys (always indexed) and the `UNIQUE` constraints noted per-table above (which SQLite/PostgreSQL both index automatically):

| Table | Index | Purpose |
|---|---|---|
| `users` | `email` (unique) | login lookup, signup uniqueness check |
| `users` | `organization_id` | listing users per org (future multi-user feature) |
| `sessions` | `user_id` | session lookup/revocation per user |
| `sessions` | `expires_at` | periodic cleanup sweep of expired sessions |
| `password_reset_tokens` | `user_id` | lookup during reset flow |
| `datasets` | `organization_id` | listing an org's datasets (`GET /api/datasets`) |
| `datasets` | `created_at` | recency sort/pagination |
| `customers` | `organization_id` | tenant isolation filter on every customer query |
| `customers` | `dataset_id` | listing customers per dataset |
| `models` | `organization_id` | listing an org's model versions (`GET /api/models`) |
| `models` | `(organization_id, model_type, is_active)` composite | fast "find the org's active company model" lookup used on every prediction request |
| `training_jobs` | `organization_id` | listing an org's training history |
| `training_jobs` | `created_at` | recency sort |
| `predictions` | `organization_id` | tenant isolation filter on every prediction query |
| `predictions` | `model_id` | model-detail "predictions made with this version" |
| `predictions` | `customer_id` | customer-detail prediction history (`GET /api/customers/:id`) |
| `predictions` | `batch_job_id` | grouping/retrieving a batch run's rows |
| `predictions` | `created_at` | dashboard trend queries, recency sort/pagination |
| `audit_logs` | `organization_id` | org-scoped audit trail |
| `audit_logs` | `created_at` | recency sort/pagination |

Composite indexes are chosen based on the actual query patterns implied by `API.md` (e.g., every list/filter endpoint documented there), not added speculatively.

---

## 5. Constraints (summary)

- **NOT NULL** on every column marked so in §2 — enforced at the DB layer, not just application validation, so a bug in a service can never silently write an incomplete row.
- **UNIQUE**: `users.email`, `datasets.storage_path`, `models.artifact_path`, `explanations.prediction_id`.
- **CHECK constraints** on every enum-like text column (`source_type`, `model_type`, `algorithm`, `status`, `prediction_type`, `risk_level`, `event_type`, `theme_preference`) so an invalid value can never be written even if application-layer validation is bypassed or has a bug.
- **CHECK (`churn_probability` between 0 and 1)** on `predictions` — a structural guarantee that no out-of-range value is ever stored, reinforcing the "no hard-coded/implausible values" rule with an actual DB-level guard.
- **Foreign key constraints** per §3, enforced via `PRAGMA foreign_keys = ON` in SQLite and natively in PostgreSQL.
- **Application-level constraint** (not a raw SQL constraint, due to SQLite's limited partial-unique-index support in the version targeted for V1): at most one active `company_specific` model per organization — enforced transactionally in the `models` service layer (§2.7); becomes a real partial unique index (`WHERE model_type = 'company_specific' AND is_active`) on PostgreSQL (§8).

---

## 6. Ownership, Tenant Isolation & Security

- **Binding rule:** every query against `datasets`, `customers`, `models` (except the shared `organization_id IS NULL` baseline), `training_jobs`, `predictions`, `explanations`, and `audit_logs` filters by the requesting user's `organization_id`. This is enforced at the service layer via `BACKEND_SPEC.md §4`'s `@ownership_required` decorator / query-scoping helper — never left to the client-supplied id alone.
- **No cross-tenant reads by id-guessing (IDOR):** because every scoped table carries `organization_id` and every query filters on it, requesting another organization's resource by numeric id returns `404 NOT_FOUND` (not `403`, to avoid confirming the resource's existence to an unauthorized caller) rather than leaking data.
- **`explanations`** inherits its access scope through `predictions.organization_id` — there is no independent tenant check needed on `explanations` directly since it's always fetched via its owning prediction.
- **Audit trail:** `audit_logs` is append-only from the application's perspective (no update/delete route exists for it in `API.md`); it exists specifically so tenant-isolation and security-relevant events (login, dataset upload/delete, training, model activation, predictions) are reconstructable after the fact.
- **Password/token secrecy:** `users.password_hash` and `password_reset_tokens.token_hash` are the only credential-adjacent columns in the schema; the raw password and raw reset token are never persisted anywhere, consistent with `BACKEND_SPEC.md §4/§9`.
- **Cross-tenant test coverage:** `BACKEND_SPEC.md §8` requires a dedicated test suite asserting a second test organization can never read the first organization's rows through any endpoint, including by guessing sequential ids — this is the DB-layer contract that suite verifies.

---

## 7. SQLite Implementation Notes (V1)

- Single SQLite file on PythonAnywhere's persistent storage, outside any web-served or Git-tracked path (`DEPLOYMENT.md §1/§5`).
- `PRAGMA foreign_keys = ON` set on every connection (SQLite defaults this off).
- `JSON` columns use SQLAlchemy's `JSON` type, which SQLite stores as `TEXT` transparently — application code always reads/writes through the ORM's JSON (de)serialization, never raw string concatenation.
- SQLite's single-writer behavior is an accepted V1 constraint given the expected scale (PROJECT_SPEC §49 V1 scope, §51 Technical Risks) — write-heavy operations (batch prediction inserts, training-job status updates) are kept short-lived per transaction to minimize lock contention.
- No SQLite-only syntax (e.g., `AUTOINCREMENT` quirks, `WITHOUT ROWID` tables, SQLite-specific pragmas beyond the FK one above) is relied upon anywhere in the schema, keeping §8's migration mechanical.

## 8. Future PostgreSQL Migration Path

1. Provision a PostgreSQL instance; set `DATABASE_URL` to point at it (`DEPLOYMENT.md §2`).
2. Run `alembic upgrade head` against the new database — the same migration chain used for SQLite applies unchanged, since every type and constraint used is portable (§2–§5).
3. Add the one constraint that SQLite couldn't express as a real index (§5's "at most one active company model per org") as an actual partial unique index: `CREATE UNIQUE INDEX ... ON models (organization_id) WHERE model_type = 'company_specific' AND is_active`.
4. Run a one-off data-migration script (`scripts/migrate_sqlite_to_postgres.py`, created when this phase is actually undertaken — not part of V1) to copy every row table-by-table in FK-safe order (`organizations` → `users` → `sessions`/`password_reset_tokens` → `datasets` → `customers` → `models` → `training_jobs` (backfilling `resulting_model_id`) → `predictions` → `explanations` → `audit_logs`).
5. Update `MODEL_ARTIFACT_DIR` / file-storage configuration if the hosting target changes alongside the database (a database migration does not itself require a hosting migration).
6. No ORM model changes are required — the schema was designed portable from the start (see the opening statement at the top of this document).
