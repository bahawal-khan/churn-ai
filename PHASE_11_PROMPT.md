# Phase 11 — Full Integration, Testing & Security Hardening

## Objective
Complete Phase 11 by fully integrating and testing the existing ChurnAI frontend, Flask backend, database, and ML pipeline. Improve reliability, integration coverage, CI, and security without adding new product scope.

## Scope

### 1. Frontend ↔ Backend Integration
Verify real end-to-end flows:
- Signup → authenticated session → Dashboard
- Login → Dashboard
- Logout → session cleared → redirect
- CSV upload → data-quality report
- Invalid/malformed CSV → proper validation/error state
- Training blocked when the required target column is missing
- Valid training continues through the real backend/ML flow
- Batch prediction → polling → completed results → CSV download

### 2. CORS
Implement secure CORS:
- Explicit allow-list only; never `*`
- Allow `http://localhost:3000`
- Configure intended production frontend origin(s)
- Preserve required credential/cookie behavior
- Test allowed and rejected origins

### 3. Rate Limiting
Add Flask-Limiter or the approved equivalent to:
- `/api/auth/*`
- Training endpoints
- Prediction endpoints

Requirements:
- HTTP `429`
- Existing error envelope with `RATE_LIMITED`
- Automated tests
- Configurable limits
- Normal development/tests remain usable

### 4. CI
Create GitHub Actions CI for push and pull requests:
- Backend pytest
- ML pytest
- Frontend Jest/tests
- Frontend production build
- CI must fail when required tests/build fail
- No deployment work in this phase

### 5. Security Hardening
Verify:
- Cross-tenant ownership / IDOR
- Authentication/authorization
- Secure session-cookie configuration
- Sanitized client-facing errors
- `.env` and secret hygiene
- CORS
- Rate limiting

Only fix genuine issues found; do not rewrite working security architecture.

### 6. Manual QA
Create `docs/QA_CHECKLIST.md` covering:
- Every existing frontend page
- Dark/light mode
- Desktop/tablet/mobile
- Navigation
- Authentication
- CSV upload
- Training
- Prediction
- Analytics
- Models
- Reports
- Settings
- Loading/empty/error states

## Strict Out-of-Scope
Do NOT:
- Add new product features or frontend pages
- Add new ML algorithms/features
- Change ML behavior unless a genuine integration bug is found
- Change DB schema unless genuinely required by an integration/security issue
- Implement deployment or Vercel/PythonAnywhere configuration
- Add multi-org UI, editable risk thresholds, XLSX ingestion, or other future-scope items

## Acceptance Criteria

### Integration
- [ ] Signup → Dashboard passes
- [ ] Login → Dashboard passes
- [ ] Logout clears session and redirects correctly
- [ ] Bad CSV produces the correct validation/data-quality state
- [ ] Training is blocked without the required target column
- [ ] Batch prediction polling completes correctly
- [ ] Completed batch prediction enables CSV download
- [ ] Real frontend/backend integration remains functional

### CORS
- [ ] Explicit allow-list implemented
- [ ] `http://localhost:3000` works
- [ ] Production frontend origin(s) are configurable
- [ ] No wildcard `*`
- [ ] Credentials/cookies continue working
- [ ] Non-allow-listed origin is rejected
- [ ] CORS tests pass

### Rate Limiting
- [ ] Auth endpoints are rate limited
- [ ] Training endpoints are rate limited
- [ ] Prediction endpoints are rate limited
- [ ] Exceeded limits return `429`
- [ ] Response uses `RATE_LIMITED`
- [ ] Rate-limit tests pass
- [ ] Limits are configurable
- [ ] Normal development/test workflows remain usable

### CI
- [ ] GitHub Actions workflow exists
- [ ] Backend tests run
- [ ] ML tests run
- [ ] Frontend tests run
- [ ] Frontend production build runs
- [ ] Runs on push and pull request
- [ ] Fails on test/build failure

### Security
- [ ] Cross-tenant isolation remains enforced
- [ ] No obvious IDOR vulnerability
- [ ] Protected routes require authentication
- [ ] Session-cookie security verified
- [ ] Sensitive/internal errors are not exposed
- [ ] Secrets are not hardcoded/committed
- [ ] CORS is not overly permissive
- [ ] Rate limiting protects sensitive/high-cost endpoints

### QA
- [ ] `docs/QA_CHECKLIST.md` exists
- [ ] All existing pages are covered
- [ ] Dark/light themes checked
- [ ] Desktop/tablet/mobile checked
- [ ] Loading/empty/populated/error states checked
- [ ] Auth flows checked
- [ ] Upload/training/prediction flows checked

### Regression
- [ ] Backend tests pass
- [ ] ML tests pass
- [ ] Frontend tests pass
- [ ] New Phase 11 tests pass
- [ ] Frontend production build succeeds
- [ ] Phase 7–10 functionality remains intact
- [ ] No new product scope introduced

## Required Final Report
At completion, report:
1. Files changed
2. Implementation summary
3. Security findings/fixes
4. Integration test results
5. Backend test results
6. ML test results
7. Frontend test results
8. Production build result
9. CI result
10. Manual QA result
11. PASS/FAIL for every acceptance criterion
12. Known limitations

Do NOT commit automatically. Stop after verification and wait for approval to commit.
