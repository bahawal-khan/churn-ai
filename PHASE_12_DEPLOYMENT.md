# PHASE 12 — Deployment

## Objective

Deploy the existing ChurnAI application to the free-tier architecture defined by the project specifications:

- Frontend → Vercel
- Backend → PythonAnywhere
- Database → existing SQLite deployment approach
- Model artifacts → PythonAnywhere persistent storage

This phase is deployment/infrastructure only. Do not add product features or change the existing ML/product scope.

## Instructions

First read and follow these project sources before making changes:

- `PROJECT_SPEC.md`
- `DEPLOYMENT.md`
- `DATABASE_SPEC.md`
- `PHASE_11_PROMPT.md`
- `docs/QA_CHECKLIST.md`

Inspect the actual repository state before changing anything.

### 1. GitHub

- Verify the repository has a GitHub remote.
- If no remote exists, stop and tell me that I must provide/configure the repository remote.
- Do not invent credentials or repository URLs.
- Push only after I explicitly approve if pushing requires an external account action.

### 2. Backend — PythonAnywhere

Deploy the existing Flask backend to PythonAnywhere free tier.

Requirements:

- Use the existing Flask application factory: `backend.app.create_app()`.
- Configure the PythonAnywhere WSGI entry point correctly.
- Install `backend/requirements.txt`.
- Configure production environment variables securely.
- Run Alembic migrations against the production SQLite database.
- Ensure the SQLite parent directory exists and is writable.
- Keep the database outside web-served and git-tracked locations.
- Transfer existing model artifacts to persistent `ml/artifacts/` storage through a non-git method.
- Run the existing `scripts/seed_baseline_model.py` once artifacts/database are ready.
- Reload the application.
- Verify `/api/health`.

Expected health contract:
- `status: ok`
- `db: ok`
- `model_loaded: true`

Do not commit SQLite files, model artifacts, `.env` files, or secrets.

### 3. Backend Production Environment

Configure production values securely:

- `FLASK_ENV`
- `SECRET_KEY`
- `DATABASE_URL`
- `CORS_ALLOWED_ORIGINS`
- `SESSION_COOKIE_SECURE=true`
- `SESSION_TTL_DAYS`
- `MAX_UPLOAD_SIZE_MB`
- `PASSWORD_RESET_TOKEN_TTL_MINUTES`
- Phase 11 `CHURNAI_RATE_LIMIT_*` variables

Never print or expose secret values in the final report.

Production `SECRET_KEY` must be unique and must not be the development/default key.

CORS must contain the real deployed Vercel origin(s), never `*`.

### 4. Environment Documentation

If missing and genuinely needed, create `backend/.env.example`.

It must contain variable names/placeholders only. Never put real secrets in it.

Update `DEPLOYMENT.md` with genuine deployment findings, especially final environment-variable names, rate-limit variables, PythonAnywhere timeout/CPU behavior, and deployment-specific configuration. Do not rewrite unrelated documentation.

### 5. Frontend — Vercel

Deploy the existing `frontend/` application to Vercel.

Requirements:

- Use `frontend/` as the Vercel project/root directory.
- Do not create unnecessary `vercel.json`.
- Configure `NEXT_PUBLIC_API_BASE_URL` for Preview and Production as appropriate.
- Ensure the Vercel build succeeds.
- Preserve all existing routes and functionality.
- Do not add new pages/features.

### 6. Cross-Origin Authentication

After both services are live, verify in a real browser:

1. Open Vercel frontend.
2. Signup.
3. Login/session is established.
4. Navigate to Dashboard.
5. Session persists across navigation/refresh.
6. Upload a valid CSV.
7. Run prediction.
8. Dashboard/analytics reflect real backend data.
9. Logout.
10. Protected routes redirect appropriately.

Verify CORS, cookies, `HttpOnly`, `SameSite`, and `Secure` behavior.

### 7. Model / ML Verification

Use the existing trained artifacts only.

Verify:
- baseline model is seeded
- model loading succeeds
- prediction works against deployed backend
- existing model behavior remains unchanged

Do not introduce a new model.

### 8. Free-Tier Runtime Verification

Because training and batch prediction currently run synchronously, test actual PythonAnywhere free-tier behavior.

Verify single prediction, batch prediction, and existing training flow.

Do NOT build an async queue automatically. If synchronous processing is impossible because of actual free-tier limits, stop and report the evidence before changing architecture.

## Strict Out-of-Scope

Do NOT:
- Add new product features/pages
- Change frontend product content
- Add new ML algorithms/features
- Migrate SQLite to PostgreSQL
- Add multi-org UI
- Add editable risk thresholds
- Add XLSX ingestion
- Add paid infrastructure
- Add an async queue unless real platform testing proves it necessary
- Commit secrets, databases, or model artifacts
- Change unrelated architecture

## Acceptance Criteria

### GitHub
- [ ] GitHub remote exists and points to the intended repository.
- [ ] Required deployment source is available to Vercel/PythonAnywhere.

### PythonAnywhere Backend
- [ ] Flask backend is deployed successfully.
- [ ] WSGI loads `backend.app.create_app()`.
- [ ] Production dependencies install successfully.
- [ ] Production SQLite database is configured correctly.
- [ ] `alembic upgrade head` succeeds.
- [ ] Baseline model seed succeeds.
- [ ] Required model artifacts are present on persistent storage.
- [ ] `/api/health` reports healthy DB and loaded model.

### Production Configuration
- [ ] Production `SECRET_KEY` is unique and not the development/default key.
- [ ] `SESSION_COOKIE_SECURE=true`.
- [ ] `CORS_ALLOWED_ORIGINS` contains the real Vercel origin(s).
- [ ] CORS never uses `*`.
- [ ] Rate-limit configuration is appropriate.
- [ ] No secrets are committed.
- [ ] `backend/.env.example` exists if needed and contains no real secrets.

### Vercel Frontend
- [ ] Frontend is deployed from `frontend/`.
- [ ] Vercel build succeeds.
- [ ] `NEXT_PUBLIC_API_BASE_URL` points to the live backend.
- [ ] Existing 22 routes remain functional.
- [ ] No new product scope was introduced.

### Real Browser Integration
- [ ] Signup works against the live backend.
- [ ] Login works.
- [ ] Session persists after navigation/refresh.
- [ ] Dashboard loads real backend data.
- [ ] CSV upload works.
- [ ] Prediction works.
- [ ] Dashboard/analytics reflect real prediction data.
- [ ] Logout works.
- [ ] Protected routes redirect after logout.
- [ ] Cross-origin CORS works.
- [ ] Production cookies work correctly.

### ML / Runtime
- [ ] Existing baseline model loads.
- [ ] Real prediction works.
- [ ] Batch prediction behavior is verified.
- [ ] Synchronous processing is tested against actual PythonAnywhere free-tier limits.
- [ ] No unnecessary async architecture was introduced.

### QA
- [ ] `docs/QA_CHECKLIST.md` is executed against the live deployment.
- [ ] Dark mode checked.
- [ ] Light mode checked.
- [ ] Desktop checked.
- [ ] Tablet checked.
- [ ] Mobile checked.
- [ ] Public pages checked.
- [ ] Authentication pages checked.
- [ ] Dashboard checked.
- [ ] Upload/training/prediction flows checked.
- [ ] Analytics/models/reports/settings checked.
- [ ] Loading, empty, populated, and error states checked.

## Final Report

After implementation and verification, provide:

1. Files changed
2. GitHub repository/remote status
3. Vercel deployment URL
4. PythonAnywhere backend URL
5. Environment variable names configured — never secret values
6. Database migration result
7. Baseline model seed result
8. Model artifact verification
9. `/api/health` result
10. CORS result
11. Production authentication/session result
12. End-to-end smoke-test result
13. PythonAnywhere runtime/timeout findings
14. Manual QA result
15. Test/build results
16. PASS/FAIL for every acceptance criterion
17. Known limitations
18. Any item blocked by an external account/action

## Commit Rule

Do NOT commit automatically.

After deployment and verification, stop and wait for my explicit approval before creating the Phase 12 commit.
