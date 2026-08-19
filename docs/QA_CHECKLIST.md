# ChurnAI — Manual QA Checklist (QA_CHECKLIST.md)

Companion to `PROJECT_SPEC.md` §30 and `FRONTEND_SPEC.md` §25 ("Visual/manual
QA checklist (Phase 11)"). Run this checklist by hand before each deployment
(`PROJECT_SPEC.md` §30: "manual QA checklist for full user journeys before
each deployment"). Automated coverage (backend/ML pytest, frontend Jest,
CI) does not replace this — it catches what those layers can't: real visual
rendering, real browser behavior, and real cross-device layout.

**How to use this document:** run the full local stack (`backend` via
`flask run` / `python -m backend.app`, `frontend` via `npm run dev`), then
work top to bottom. Check each box as it passes; note the date, tester, and
any failures in the "Notes" column. A failing item blocks deployment until
fixed or explicitly waived by the project owner.

- **Date run:** ____________________
- **Tester:** ____________________
- **Build/commit:** ____________________

---

## 1. Cross-Cutting Checks (repeat for every page below)

For **every** page listed in §3, verify all of the following before checking
that page off:

| # | Check | Dark | Light |
|---|---|---|---|
| 1 | Page renders with no visual glitches, unstyled flashes, or layout shift | ☐ | ☐ |
| 2 | Text/background contrast is readable (no invisible text, no low-contrast body copy) | ☐ | ☐ |
| 3 | Focus states are visible when tabbing through interactive elements | ☐ | ☐ |

And at each breakpoint:

| # | Breakpoint | Check |
|---|---|---|
| 1 | Desktop (≥1280px) | Layout uses available width sensibly; no orphaned whitespace or overflow |
| 2 | Tablet (~768px) | Sidebar/nav collapses or adapts correctly; content reflows without overlap |
| 3 | Mobile (~375px) | Nav becomes a drawer/hamburger; tables/charts scroll horizontally inside their own container (page itself never scrolls horizontally); tap targets are large enough |

And for every data-bearing page/section:

| # | State | Check |
|---|---|---|
| 1 | Loading | Skeleton loader shown, not a blank page or layout jump on data arrival |
| 2 | Empty | Honest "no data yet" message + a clear next action — never a fake/placeholder number (`PROJECT_SPEC.md` binding rule) |
| 3 | Populated | Real data renders correctly, correctly formatted (numbers, dates, percentages) |
| 4 | Error | `ErrorState` renders with a retry affordance; no raw stack trace or internal error text leaks to the UI |

---

## 2. Navigation & Layout

- [ ] Sidebar nav lists every section (Dashboard, Upload, Train, Predict, Customers, Analytics, Models, Reports, Settings, Help)
- [ ] Active nav item is visually indicated
- [ ] Topbar search submits to `/customers?search=...` and returns matching results
- [ ] Theme toggle switches instantly and persists across reload (`ThemeProvider`)
- [ ] Notification bell shows recent training activity, or "No recent activity yet." when empty
- [ ] User menu shows name/email, links to Settings, and Log out works (see §4)
- [ ] Mobile: hamburger opens the nav drawer; closing it (backdrop tap / close button) works
- [ ] Footer renders on marketing pages with correct links (About, Features, FAQ, Privacy, Terms, Contact)

---

## 3. Pages

### 3.1 Marketing (public, unauthenticated)

- [ ] `/` (Landing) — hero, feature highlights, CTA to signup all render; CTA navigates correctly
- [ ] `/about`
- [ ] `/contact`
- [ ] `/privacy`
- [ ] `/terms`

### 3.2 Auth

- [ ] `/signup` — form validates full name, email format, password policy (live strength meter), confirm-password match; successful signup redirects to `/dashboard` and the session persists on reload
- [ ] `/signup` — duplicate email shows "an account with this email already exists" inline, no redirect
- [ ] `/login` — successful login redirects to `/dashboard`; wrong credentials show a generic invalid-credentials message
- [ ] `/login`, `/signup` — visiting while already authenticated redirects away to `/dashboard`
- [ ] `/forgot-password` — submitting always shows the same neutral confirmation regardless of whether the email exists
- [ ] `/reset-password` — valid token resets the password and revokes existing sessions; invalid/expired/reused token shows a clear error
- [ ] Logging out from the Topbar clears the session and redirects to `/login`; reloading a protected page afterward redirects to `/login` (not a flash of protected content)
- [ ] Visiting any `(app)` route directly while unauthenticated redirects to `/login`

### 3.3 Dashboard (`/dashboard`)

- [ ] KPI cards (Total Customers, At Risk, Predicted Churn Rate, High Risk Customers, Avg Churn Probability, model status) show real computed values
- [ ] Churn risk distribution donut renders from real data
- [ ] Churn trend line — real computed trend once predictions exist; honest empty state before that (never a synthetic-looking mock trend)
- [ ] Top churn drivers (global SHAP) list renders, with the "correlation, not causation" disclaimer visible
- [ ] Recent predictions table is sortable, paginated, and each row links to the customer detail page
- [ ] Risk-by-segment view renders from a real schema-backed cut (e.g. contract type)
- [ ] Recent uploads panel lists real uploads
- [ ] Active model card shows name, version, AUC, trained-on date — or an honest "no active model" state
- [ ] First-time visit shows the guided walkthrough; it's dismissible and replayable from Help

### 3.4 Upload (`/upload`)

- [ ] Dropzone accepts drag-and-drop and click-to-browse
- [ ] Non-`.csv` file is rejected client-side with a clear message, no network call made
- [ ] Empty file and oversized (>25MB) file are rejected client-side
- [ ] Valid CSV uploads with a visible progress indicator
- [ ] Preview table renders the first rows of the uploaded file
- [ ] Column Mapping panel shows matched/unmatched columns for confirmation
- [ ] Data Quality Report renders every check (pass/warn/fail) with plain-language detail for failures
- [ ] A file with a churn/outcome column shows the "can be used for training" badge; one without shows "predictions only"
- [ ] Upload History table lists past uploads and updates immediately after a new upload

### 3.5 Train Model (`/train`)

- [ ] Dataset dropdown lists uploaded datasets; target-column dropdown lists that dataset's columns
- [ ] "Start Training" stays disabled until both a dataset and a target column are selected
- [ ] Starting training against a dataset/column with no valid binary target shows the exact `TRAINING_LABELS_REQUIRED` message and the "you can still use the baseline model" alternative — training does not proceed
- [ ] Starting training against a valid dataset+target column runs the real backend/ML training flow end to end and reaches a terminal (`completed`/`failed`) status
- [ ] A completed job's metrics (accuracy/precision/recall/F1/ROC-AUC/PR-AUC) render
- [ ] Job history list shows past runs with status

### 3.6 Predict — Single (`/predict`)

- [ ] Form covers all required input fields; submitting with missing/invalid fields shows inline validation
- [ ] Successful prediction shows probability, predicted class, risk level, and ranked local SHAP factors
- [ ] The "correlation, not causation" disclaimer is visible on the explanation panel

### 3.7 Predict — Batch (`/predict`, batch panel)

- [ ] Uploading a batch CSV runs prediction and reaches a completed state (`batch_job_id`, summary counts)
- [ ] Summary counts (total/scored/failed rows, predicted churners, risk-level counts) match the returned results
- [ ] Rows that failed validation show their specific error reason, with no fake probability substituted
- [ ] "Download Results CSV" is enabled once results are in, and produces a CSV containing original columns + `churn_probability`, `predicted_class`, `risk_level`
- [ ] The batch run and its results are retrievable afterward via the customer's prediction history (§3.8)

### 3.8 Customers (`/customers`, `/customers/[id]`)

- [ ] List is searchable, sortable, filterable, paginated
- [ ] Customer detail page shows that customer's full prediction history, including batch-predicted rows
- [ ] Empty state (no customers yet) explains the next action

### 3.9 Analytics (`/analytics`)

- [ ] Deeper EDA-style breakdowns render from the active dataset/model, not placeholder numbers
- [ ] Filters/segment cuts work and update the displayed charts

### 3.10 Models (`/models`, `/models/[id]`)

- [ ] Lists all model versions (baseline + company-specific) with metrics
- [ ] Activate/deactivate requires confirmation (`ConfirmDialog`) and updates the active model shown elsewhere (Dashboard, Predict)
- [ ] Model detail page shows full metrics, feature schema, and training metadata

### 3.11 Reports (`/reports`)

- [ ] Generating a report produces a real, downloadable export (no hardcoded numbers)
- [ ] Report history lists past generated reports

### 3.12 Settings (`/settings`)

- [ ] Profile fields (name, organization) display and update correctly
- [ ] Risk thresholds show as read-only with the "coming soon: customize thresholds" note (not editable in V1)
- [ ] Theme preference set here matches the Topbar toggle and persists

### 3.13 Help & FAQ (`/help`)

- [ ] Covers: what churn means, how to upload data, what data is required, what the probability number means, what each risk level means, what SHAP means, what company-specific training requires and why labels are mandatory
- [ ] Onboarding walkthrough is replayable from this page

---

## 4. Security-Adjacent UX Checks

- [ ] A destructive action (deleting a dataset, deactivating a model) always shows a confirmation dialog first
- [ ] No internal error text, stack trace, or file path is ever visible in a toast/error state
- [ ] Session cookie is not readable from `document.cookie` in the browser console (confirms `HttpOnly`)
- [ ] Switching to a second account (different browser profile/incognito) never shows the first account's data anywhere (cross-tenant isolation)

---

## 5. Sign-off

| Area | Result | Notes |
|---|---|---|
| Navigation & layout | ☐ Pass ☐ Fail | |
| Marketing pages | ☐ Pass ☐ Fail | |
| Auth flows | ☐ Pass ☐ Fail | |
| Dashboard | ☐ Pass ☐ Fail | |
| Upload | ☐ Pass ☐ Fail | |
| Training | ☐ Pass ☐ Fail | |
| Prediction (single) | ☐ Pass ☐ Fail | |
| Prediction (batch) | ☐ Pass ☐ Fail | |
| Customers | ☐ Pass ☐ Fail | |
| Analytics | ☐ Pass ☐ Fail | |
| Models | ☐ Pass ☐ Fail | |
| Reports | ☐ Pass ☐ Fail | |
| Settings | ☐ Pass ☐ Fail | |
| Help & FAQ | ☐ Pass ☐ Fail | |
| Security-adjacent UX | ☐ Pass ☐ Fail | |

**Overall: ☐ Ready to deploy ☐ Blocked (see notes above)**
