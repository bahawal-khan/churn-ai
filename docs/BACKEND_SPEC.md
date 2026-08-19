# ChurnAI — Backend Specification (BACKEND_SPEC.md)

Companion to `PROJECT_SPEC.md`. Python + Flask backend, deployed on PythonAnywhere.

---

## 1. Architecture & Layering

```
routes/        → thin HTTP handlers: parse request, call one service method, return response
services/       → business logic (upload handling, training orchestration, prediction, analytics)
ml/             → shared with the ML layer: preprocessing, inference, SHAP (imported by services)
db/             → SQLAlchemy models + query helpers (imported by services, never by routes directly)
validation/     → request/file schema validation (Marshmallow or Pydantic — pinned: Pydantic, for
                   type-hint-native validation consistent with the rest of the typed codebase)
auth/           → password hashing, session/token issuance & verification, `@login_required` decorator,
                   `@ownership_required` decorator (checks the requested resource belongs to the caller's org)
errors/         → custom exception classes + a Flask error handler mapping them to the standard envelope
config.py       → environment-driven settings (dev/test/prod), loaded via `python-dotenv` locally
app.py          → application factory (`create_app()`), blueprint registration, CORS, error handler wiring
```

Rule: a route file never imports `db/` or `ml/` directly — only its matching `services/` module. This keeps routes trivially testable and keeps business logic reusable (e.g., the same `training_service.train_model()` call is used whether triggered synchronously in dev or from a background job in production).

## 2. Route Groups (blueprints)

| Blueprint | Prefix | Responsibility |
|---|---|---|
| `auth` | `/api/auth` | signup, login, logout, forgot-password, reset-password, session check |
| `datasets` | `/api/datasets` | upload, list, get, data-quality report, delete |
| `training` | `/api/training` | start training job, get job status, list model candidates |
| `models` | `/api/models` | list model versions, get model detail/metrics, activate/deactivate |
| `predictions` | `/api/predictions` | single prediction, batch prediction (upload + poll/download), prediction history |
| `customers` | `/api/customers` | list, detail (with prediction history) |
| `analytics` | `/api/analytics` | dashboard KPIs, churn trend, top drivers, risk-by-segment |
| `reports` | `/api/reports` | generate/download report exports |
| `health` | `/api/health` | uptime/health check (used by deployment monitoring, unauthenticated) |

Full request/response contracts for every route are defined in `API.md` — this document defines the architecture and cross-cutting concerns, `API.md` is the exhaustive contract.

## 3. Async Work (Training & Large Batch Prediction)

PythonAnywhere free tier has request time limits, so long-running work (model training, large batch prediction) is designed around an **API-level job pattern** that does not assume any particular execution mechanism underneath:

- `POST /api/training/jobs` creates a `training_jobs` row (status `queued`) and returns immediately with the job id. The API contract (`API.md`) and the DB state machine (`DATABASE_SPEC.md`) are fixed; what actually advances the job from `queued` to `training` to `completed` is an implementation detail chosen in Phase 8.
- Frontend polls `GET /api/training/jobs/{id}` for status (`queued → validating → preprocessing → training → evaluating → completed | failed`), matching the workflow state machine in PROJECT_SPEC §16. This polling contract is stable regardless of what runs the job underneath it.
- Batch prediction over a large CSV follows the same job-status pattern (`queued → processing → completed | failed`) once file size exceeds a documented inline-processing threshold; small batches are processed synchronously within a single request for a faster UX.
- **The specific PythonAnywhere execution mechanism is intentionally not pinned in this specification.** PythonAnywhere's background/scheduled-task support varies by account tier and can change; assuming a specific mechanism (e.g., a specific "always-on task" feature) here risks specifying something the actual free-tier account can't do. At the start of Phase 8, the actual available options are verified against the live PythonAnywhere account, and the **simplest mechanism that satisfies the job-status contract above** is chosen — candidates to evaluate at that time include a scheduled task, an always-on task if the account tier supports it, or, if neither is available, keeping work synchronous within request-time limits for the dataset sizes ChurnAI actually expects in V1 (with the size threshold adjusted accordingly). Whichever option is chosen is recorded in this section as an addendum once Phase 8 implementation confirms it — this document does not commit to one in advance.

## 4. Authentication

- **Password hashing:** `argon2` (via `argon2-cffi`) — chosen over bcrypt for stronger modern defaults and no 72-byte input truncation footgun; hash + verify wrapped in `auth/password.py`.
- **Session mechanism:** signed, HttpOnly, `Secure`, `SameSite=Lax` session cookie issued on login, containing a server-side session id; session records stored in the `sessions` table (or short-lived JWT access token + rotating refresh token stored as an HttpOnly cookie — final pick: **cookie-based server session**, simpler to invalidate correctly on logout/password-reset than stateless JWT, and appropriate at V1 scale). Decision documented here as binding for Phase 9. Each session has a fixed absolute TTL of `SESSION_TTL_DAYS` (default 7 days, `DEPLOYMENT.md §2`) from issuance, written to `sessions.expires_at` (`DATABASE_SPEC.md §2.3`) at creation — not a sliding/renewing window in V1.
- **Password policy:** min 8 characters, ≥1 uppercase, ≥1 lowercase, ≥1 digit, ≥1 special character — validated both client-side (UX) and server-side (source of truth).
- **Signup flow:** validate email format → check uniqueness (case-insensitive) → validate password policy → hash password → create `users` row + a default `organizations` row for that user → issue session → return user profile (never the password hash).
- **Login flow:** look up by email → verify hash → issue session → return user profile. Generic "invalid email or password" message on any failure (no user-enumeration hint via error message wording, though uniqueness-check messaging on signup does confirm existing accounts — an accepted, documented V1 trade-off, mitigated by rate limiting).
- **Forgot/reset password:** generate a single-use, time-limited (e.g., 30 minute) reset token, store its hash (not the raw token) with an expiry in a `password_reset_tokens` table, send/return the raw token via the configured email provider (or logged in local dev if none configured), reset endpoint validates token hash + expiry, sets new password, invalidates the token and all existing sessions for that user.
- **Route protection:** `@login_required` decorator checks the session cookie server-side and attaches `current_user` to the request context; every non-auth, non-health route uses it. `@ownership_required` (or an equivalent query-scoping helper) ensures every DB query for datasets/models/predictions/customers is filtered by the caller's `organization_id` — never trusts an id in the URL alone.
- **Session persistence across refresh:** the frontend calls `GET /api/auth/session` on app load; a valid cookie returns the current user and the app renders as logged in without re-prompting for credentials.

## 5. Validation Layer

- Every route with a request body/file validates it against a Pydantic model before calling its service.
- File upload validation (§6) runs before any CSV parsing is attempted at scale (cheap checks first: extension, size, MIME sniffing) — expensive checks (full parse, schema/quality validation) run only after cheap checks pass.
- Validation errors return HTTP 422 with the standard error envelope and field-level details.

## 6. File Handling

- Accepted: `.csv` only in V1, max size documented as **25 MB** (chosen to stay comfortably within PythonAnywhere free-tier request/storage limits; revisited if real usage patterns demand it).
- Server generates a UUID-based storage filename; the original filename is stored only as display metadata (`datasets.original_filename`), never used to construct a filesystem path.
- Storage directory is outside any statically-served path.
- Upload pipeline: extension/size check → MIME sniff → encoding check (UTF-8; explicit friendly error otherwise) → CSV parse with ragged-row detection → schema check (matches known schema pattern? which columns map to known fields?) → hand off to `DataQualityValidator` (ML_SPEC §3) → store dataset row + quality report → return report to client for the Preview/Data Quality Report UI step.
- Internal paths, stack traces, and library exception text are never included in any client-facing response.

## 7. Error Handling

Standard envelope for every error response:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The uploaded file is missing required columns: Contract, Payment Method.",
    "details": { "missing_columns": ["Contract", "Payment Method"] }
  }
}
```

| Category | HTTP status | Example code |
|---|---|---|
| Auth failure (bad credentials) | 401 | `INVALID_CREDENTIALS` |
| Expired/invalid session | 401 | `SESSION_EXPIRED` |
| Unauthorized (not your resource) | 403 | `FORBIDDEN` |
| Not found | 404 | `NOT_FOUND` |
| Duplicate email | 409 | `EMAIL_ALREADY_EXISTS` |
| Invalid/malformed data or CSV | 422 | `VALIDATION_ERROR`, `MALFORMED_CSV` |
| Missing required columns | 422 | `SCHEMA_MISMATCH` |
| File too large | 413 | `FILE_TOO_LARGE` |
| Training precondition failed (no target labels) | 422 | `TRAINING_LABELS_REQUIRED` |
| Training/prediction runtime failure | 500 | `TRAINING_FAILED` / `PREDICTION_FAILED` |
| Database error | 500 | `DATABASE_ERROR` |
| Rate limit exceeded | 429 | `RATE_LIMITED` |
| Unexpected server error | 500 | `INTERNAL_ERROR` |

Every exception is logged server-side with full context (stack trace, request id, user id if available); only the sanitized `code`/`message`/`details` shape ever reaches the client. A `request_id` is included in every response (success or error) for support/debugging correlation with server logs.

## 8. Testing Strategy (backend)

- **Unit tests** (`tests/backend/`): validation schemas, password hashing/verification, error-envelope mapping, service-layer functions with the DB/ML layers mocked or using an in-memory SQLite test DB.
- **Integration tests**: full request → route → service → test DB round trips for each blueprint, covering documented happy paths and the documented error codes above.
- **File upload tests**: valid CSV, malformed CSV, oversized file, wrong extension, missing columns, empty file, duplicate columns — each asserted against the exact expected error code.
- **Auth tests**: signup, duplicate email, weak password rejection, login success/failure, session persistence, logout invalidation, expired/invalid token on reset, protected-route rejection without a session.
- Run via `pytest`; CI wiring is a Phase 11 deliverable, not required before then per the phased plan.

## 9. Security

- Argon2 password hashing; no plaintext password ever logged or stored.
- `.env`-driven `config.py`; `.env` is git-ignored from the very first commit (enforced already in `CLAUDE.md`).
- CORS: allow-list of the deployed Vercel origin(s) + `http://localhost:3000` in development; no wildcard origin.
- Cookies: `HttpOnly`, `Secure` (in production), `SameSite=Lax`.
- Input validation on every endpoint (Pydantic schemas) — no endpoint trusts client-supplied structure blindly.
- Ownership checks on every data-access query (no IDOR: a user cannot fetch another organization's dataset/model/prediction by guessing an id).
- Rate limiting: `Flask-Limiter` (in-process, suitable for the free-tier single-worker deployment) applied to `/api/auth/*` (prevent credential stuffing) and to training/prediction endpoints (prevent resource exhaustion on free-tier compute); documented upgrade path to a shared/Redis-backed limiter if the app scales beyond a single worker.
- No secrets, API keys, or `.env` files ever committed — enforced by `.gitignore` from the very first commit (prior to Phase 1 of the implementation roadmap) and spot-checked before each deployment.
