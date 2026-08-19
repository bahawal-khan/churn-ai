# ChurnAI — Deployment Specification (DEPLOYMENT.md)

Companion to `PROJECT_SPEC.md`. Target: zero-paid-infrastructure deployment.

---

## 1. Target Architecture

- **Frontend:** Vercel (free tier) — Next.js app, automatic deploys from the `frontend/` path on push to `main` (or a dedicated deploy branch).
- **Backend:** PythonAnywhere (free tier) — Flask app served via PythonAnywhere's WSGI configuration.
- **Database:** SQLite file on PythonAnywhere's persistent filesystem (outside any web-served directory).
- **Model artifacts:** stored under the top-level `ml/artifacts/` directory (`PROJECT_SPEC.md §35` — a sibling of `backend/`, not nested inside it) on PythonAnywhere's persistent storage, not committed to Git, not served statically.

## 2. Environment Variables

**Backend (`.env`, never committed):**
```
FLASK_ENV=production
SECRET_KEY=<generated, never reused across environments>
DATABASE_URL=sqlite:////home/<user>/churnai/backend/db/churnai.db
CORS_ALLOWED_ORIGINS=https://churnai.vercel.app,http://localhost:3000
SESSION_COOKIE_SECURE=true
SESSION_TTL_DAYS=7
MODEL_ARTIFACT_DIR=/home/<user>/churnai/ml/artifacts
MAX_UPLOAD_SIZE_MB=25
PASSWORD_RESET_TOKEN_TTL_MINUTES=30
```

**Frontend (`.env.local` for dev, Vercel Project Settings for prod):**
```
NEXT_PUBLIC_API_BASE_URL=https://<username>.pythonanywhere.com/api
```

`.env` / `.env.local` are git-ignored from the first commit per `CLAUDE.md`. Production secrets are set directly in PythonAnywhere's Web tab environment variables and Vercel's Project Settings → Environment Variables, never checked into the repo.

## 3. CORS

Backend CORS allow-list is exactly: the deployed Vercel domain(s) + `http://localhost:3000` for local development. No wildcard (`*`) origin in any environment. Credentials (`Access-Control-Allow-Credentials: true`) enabled since auth uses cookies.

## 4. Build & Deploy Process

**Backend (PythonAnywhere):**
1. Push to the repository; pull latest on the PythonAnywhere console (`git pull`).
2. `pip install -r requirements.txt` inside the configured virtualenv.
3. `alembic upgrade head` to apply any new migrations.
4. Reload the web app from the PythonAnywhere Web tab.
5. Hit `/api/health` to confirm the deploy.

**Frontend (Vercel):**
1. Vercel auto-builds on push (`npm install && npm run build`) once the project is connected to the `frontend/` directory (monorepo root configured in Vercel Project Settings).
2. `NEXT_PUBLIC_API_BASE_URL` set in Vercel env vars per environment (Preview vs Production) so preview deploys can point at a staging backend URL if one exists, or the same production backend during early phases.

## 5. Database Setup on First Deploy

1. Ensure the SQLite file's parent directory exists and is writable by the PythonAnywhere web app user, and is **not** inside a statically served or Git-tracked path.
2. Run `alembic upgrade head` to create all tables.
3. Seed the shared baseline model row (`models` table, `organization_id IS NULL`, `model_type = 'baseline_global'`) by running the Phase 1–7 training pipeline output artifact copy + a one-off seed script — not by hand-editing the DB.

## 6. File & Model Storage Considerations

- Uploaded CSVs and generated batch-prediction result files are stored under a dedicated, non-web-served directory with server-generated filenames (BACKEND_SPEC §6); a documented retention/cleanup policy (e.g., periodic deletion of files older than N days, configurable) avoids unbounded disk growth on the free tier's limited storage quota.
- Model artifacts (ML_SPEC §14) persist across deploys (they live outside the Git-tracked/deployed code path); redeploying the backend code does not require retraining.
- Free-tier PythonAnywhere disk quota is limited — the deployment runbook includes a periodic disk-usage check as part of routine maintenance, documented as an operational note rather than solved automatically in V1.

## 7. Known Free-Tier Constraints & Mitigations

| Constraint | Mitigation |
|---|---|
| PythonAnywhere free-tier request timeout | Long-running work (training, large batch prediction) handled via the async job-status API pattern in BACKEND_SPEC §3; the underlying execution mechanism is deliberately left unpinned in this spec and is selected during Phase 8 by verifying what the actual PythonAnywhere account tier supports, using the simplest viable option rather than assuming a specific feature is available |
| PythonAnywhere free-tier CPU seconds/day | ANN kept small (ML_SPEC §8); training scheduled rather than triggered unboundedly; documented in onboarding that training may take longer on the free tier |
| PythonAnywhere free-tier outbound network allow-list | Any third-party service the backend calls (e.g., a transactional email provider for password reset) must be on PythonAnywhere's free-tier allow-list, or reset tokens are logged server-side in early phases as a documented interim approach |
| Vercel free-tier function/build limits | Frontend is otherwise static/SSR-light for this app's needs; no heavy serverless compute expected on the frontend side |
| No paid card required | Confirmed as a hard constraint for V1 — any feature requiring a paid tier (e.g., a paid email API) needs a free-tier alternative or is deferred, documented per-case if it arises |

## 8. Monitoring

- `GET /api/health` — unauthenticated, returns `{ "status": "ok", "db": "ok", "version": "..." }`; used for manual and (if available) uptime-monitor checks.
- Server-side logging (BACKEND_SPEC §7) is the primary error-visibility mechanism for V1; a third-party error-tracking service (e.g., Sentry free tier) is a documented Future Scope addition, not required for V1 launch.
