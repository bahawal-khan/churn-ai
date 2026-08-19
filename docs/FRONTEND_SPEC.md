# ChurnAI — Frontend Specification (FRONTEND_SPEC.md)

Companion to `PROJECT_SPEC.md`, `BACKEND_SPEC.md`, `API.md`, and `DATABASE_SPEC.md`. Next.js (App Router) + TypeScript + Tailwind CSS. Every data-bearing view in this document consumes a real endpoint from `API.md` — no view in this spec is backed by placeholder or hard-coded data (binding rule, `PROJECT_SPEC.md`, top of document).

---

## 1. Stack

- **Framework:** Next.js (App Router), TypeScript throughout, no `any` in committed code without a documented reason.
- **Styling:** Tailwind CSS with a project-defined design-token config (colors, spacing, radii, shadows, typography scale) extending Tailwind's theme rather than raw utility values ad hoc.
- **Components:** small reusable primitive library (`components/ui/`) composed into feature components (`components/<feature>/`) — see §13.
- **Charts:** Recharts (donut, line, bar, radar).
- **Motion:** Framer Motion, used per the restrained rules in §12.
- **API layer:** `lib/api/client.ts` (fetch wrapper: base URL from `NEXT_PUBLIC_API_BASE_URL`, credentials included, parses the standard error envelope from `BACKEND_SPEC.md §7` into a typed `ApiError`) + one module per `API.md` resource group (`lib/api/auth.ts`, `lib/api/datasets.ts`, `lib/api/training.ts`, `lib/api/models.ts`, `lib/api/predictions.ts`, `lib/api/customers.ts`, `lib/api/analytics.ts`, `lib/api/reports.ts`). No component calls `fetch` directly.
- **Data-fetching:** server components for initial data where practical (App Router default); client components + SWR (or React Query) for interactive/polling views — training-job status (`GET /api/training/jobs/:id`) and batch-prediction status (`GET /api/predictions/batch/:id`) are polled this way.

## 2. Design System

The provided UI/UX reference image (dark, dense SaaS analytics dashboard) is used as an information-architecture reference (sidebar nav, KPI-card row, donut + trend + drivers layout, prediction/SHAP module row), not a pixel-exact spec. ChurnAI defines its own token set and adds what the reference image lacks:

- **Tokens:** a `theme.ts`/Tailwind-config-level palette with semantic names (`bg-surface`, `bg-elevated`, `text-primary`, `text-muted`, `border-subtle`, `accent-primary`, `risk-low`, `risk-medium`, `risk-high`), each with a light-mode and dark-mode value, so no component hardcodes a raw hex value.
- **Typography scale:** one heading scale (H1–H4), one body scale (base/sm/xs), one numeric/KPI display scale (used for large dashboard numbers) — defined once, reused everywhere.
- **Spacing/radius/shadow scale:** consistent 4px-based spacing scale; consistent corner radius per component tier (cards vs. buttons vs. inputs); soft elevation shadows tuned per theme (dark mode uses lighter borders more than heavy shadows, matching the reference image's aesthetic).
- **Risk color coding:** Low = green, Medium = amber, High = red in both themes, always paired with a text label/icon (not color alone — accessibility, §22).

## 3. Light / Dark Mode

- Both themes are first-class (the reference image is dark-only; ChurnAI adds light mode as a full peer, not an afterthought).
- Implemented via a `data-theme` attribute on `<html>` + CSS variables per token (§2), toggled client-side, no flash-of-wrong-theme on load (theme resolved before paint using the stored preference).
- **Persistence:** stored in `users.theme_preference` (`DATABASE_SPEC.md §2.1`) via `PATCH` on the user profile, so the preference follows the user across devices/sessions, not just `localStorage`. An unauthenticated visitor (landing page) uses OS-level `prefers-color-scheme` as the default with a manual override stored in a cookie until they sign in.
- Every component in §13 is designed and reviewed against both themes — no component ships "dark mode only" and retrofitted later.

## 4. Navbar / Sidebar Navigation

Two navigation surfaces, matching the reference image's IA:

- **Authenticated app shell — `Sidebar`:** collapsible left sidebar with sections in this order: Dashboard, Upload Data, Train Model, Predictions (Single/Batch), Customers, Analytics, Model Management, Reports, Settings, Help & Support. Active route is visually highlighted; collapses to icon-only on smaller viewports and to a slide-over drawer on mobile (§10).
- **Authenticated app shell — `Topbar`:** global search (customers/predictions/uploads — hits a lightweight `/api/customers?search=` / `/api/datasets?search=` style query), theme toggle, notifications icon (surfaces recent completed training jobs / batch predictions — read from `audit_logs`/`training_jobs`, not a separate mocked feed), user menu (profile, settings, logout).
- **Public/marketing navbar** (landing, about, privacy, terms, contact — unauthenticated): logo/wordmark, links to Features/FAQ, theme toggle, Login + Sign Up buttons. If a valid session exists, Login/Sign Up are replaced with a single "Go to Dashboard" button (checked via `GET /api/auth/session` — consistent with §6's already-logged-in redirect rule) rather than showing auth CTAs to an already-authenticated visitor.

## 5. Footer

Present on every page (marketing and authenticated app shell alike, in a lighter-weight form in the app shell if space is constrained):

```
ChurnAI
Predict. Understand. Retain.

Developed by: Bahawal Khan
GitHub:   [GITHUB_URL]
LinkedIn: [LINKEDIN_URL]
Email:    [EMAIL_ADDRESS]

About · Features · FAQ · Privacy · Terms · Contact
```

URLs are read from a single `siteConfig.ts` constants module (not hardcoded per-page) so they're set once when Bahawal supplies the real values (`PROJECT_SPEC.md §29` — still placeholders as of this spec). Footer links route to the static pages in §7.

## 6. Authentication UI

Pages: `/login`, `/signup`, `/forgot-password`, `/reset-password?token=...`.

- **Signup form:** full name, email, password, confirm password. Password field has a show/hide toggle and a live strength indicator (weak/fair/strong) evaluated against the exact policy in `BACKEND_SPEC.md §4` (≥8 chars, upper, lower, digit, special char) — client-side check mirrors the server-side source of truth, never diverges from it. Confirm-password mismatch is shown inline before submit. Duplicate-email submission surfaces the server's `409 EMAIL_ALREADY_EXISTS` as an inline field error, not a generic toast.
- **Login form:** email + password, "forgot password?" link, generic "invalid email or password" error on failure (matches `BACKEND_SPEC.md §4`'s no-enumeration wording).
- **Forgot password:** single email field; always shows the same "if an account exists, we've sent a reset link" success state regardless of whether the email is registered (matches the backend's enumeration-safe behavior).
- **Reset password:** new password + confirm, same strength indicator; expired/invalid token (`API.md`) shows a clear message with a link back to "forgot password" to request a new one.
- **Already-logged-in handling:** on mount, `/login` and `/signup` call `GET /api/auth/session`; a valid session immediately redirects to `/dashboard` without flashing the auth form.
- **Protected routes:** every route under the authenticated app shell checks session validity server-side (middleware/layout-level check calling the session endpoint) and redirects unauthenticated visitors to `/login?next=<original path>`, completing the loop back after successful login.
- **Session persistence:** cookie-based (`BACKEND_SPEC.md §4`) — a refresh does not log the user out; no client-side-only "remember me" hack standing in for real session persistence.

## 7. Landing & Static Pages

- **`/` Landing page:** hero section (product name, "Predict. Understand. Retain." tagline, primary CTA to Sign Up), a Key Features section (AI-powered churn prediction, SHAP explainability, company-specific model training, analytics dashboard — mirroring the real V1 feature set, not aspirational features not yet built), a short "how it works" strip (Upload → Train/Predict → Understand via SHAP → Act), social-proof/footer area. No fabricated testimonials or fabricated usage numbers.
- **`/about`:** product description, mission framing consistent with `PROJECT_SPEC.md §1`.
- **`/privacy`, `/terms`:** placeholder legal copy clearly marked as a template pending real legal review (not fabricated as if final) — content ownership is Bahawal's, this spec only reserves the page/route.
- **`/contact`:** the same email from the footer, plus a simple contact note (no ticketing system in V1).

## 8. Onboarding

- First dashboard visit after signup (checked via `users.onboarding_completed_at IS NULL`) triggers a 4–6 step guided tour (`OnboardingTour` component, §24): where to upload data, where predictions live, what risk badges mean, where SHAP explanations appear, where to train a company-specific model.
- Skippable and replayable from `/help`; completing or skipping calls a `PATCH` to set `onboarding_completed_at` so it does not reappear on every login.
- First appearance of each domain term (churn probability, risk level, SHAP, company-specific training) anywhere in the app carries an inline `Tooltip` sourced from one shared `glossary.ts` content module, so definitions are consistent everywhere they appear.

## 9. Dashboard (`/dashboard`)

Backed by `GET /api/analytics/dashboard`, `/risk-distribution`, `/churn-trend`, `/top-drivers`, `/segments` (`API.md`), plus `GET /api/predictions` (recent) and `GET /api/datasets` (recent uploads) and `GET /api/models` (active model card).

Required components (all four states from §11 apply to each):
- **KPI row:** Total Customers, At Risk Customers, Predicted Churn Rate, High Risk Customers, Avg Churn Probability, plus a compact active-model status chip.
- **`RiskDonutChart`** — Low/Medium/High counts.
- **`ChurnTrendChart`** — predicted churn rate over time, computed strictly from stored `predictions` history (`DATABASE_SPEC.md §2.9`); before any predictions exist, this renders its empty state, never a plausible-looking placeholder trend line.
- **`TopDriversBarList`** — global SHAP summary for the active model (`ML_SPEC.md §13`).
- **Recent Predictions `DataTable`** — sortable, paginated, links to `/customers/[id]`.
- **`SegmentRadarChart`** or bar view — risk breakdown by contract type / senior citizen / dependents (real schema cuts, `PROJECT_SPEC.md §19`), not arbitrary categories copied from the reference image.
- **Recent Uploads panel** — last few `datasets`, linking to `/upload` history.
- **Active Model card** — name, algorithm, version, key metric (e.g., AUC), trained-on date, and the synthetic-data disclaimer (`PROJECT_SPEC.md §3.1`) when the active model is the shared baseline.

## 10. CSV Upload (`/upload`)

- **`UploadDropzone`** component: drag-and-drop or click-to-browse, `.csv` only, client-side pre-check of extension/size (mirroring `BACKEND_SPEC.md §6`'s 25 MB limit) before the network call, progress indicator during upload.
- On successful upload (`POST /api/datasets`), the page shows:
  - **Preview** — first N rows as a table.
  - **Column Mapping panel** — the auto-detected schema-contract mapping from `datasets.column_mapping` (`DATABASE_SPEC.md §2.5`), editable by the user before confirming, per `PROJECT_SPEC.md §16.1`'s explicit mapping-confirmation requirement. Unmapped columns are visibly listed as "not used" rather than silently dropped.
  - **`DataQualityReportPanel`** — per-check pass/warn/fail rendering matching `ML_SPEC.md §3`'s report shape, with plain-language explanations per failed/warned check.
  - Clear next-step guidance: "This file can be used for prediction" vs. "This file includes a churn/outcome column and can be used for training" vs. a blocking explanation if the compatibility floor (`PROJECT_SPEC.md §16.1`) isn't met.
- Upload history list (paginated `GET /api/datasets`), each row linking back to its stored quality report.

## 11. Training Workflow (`/train`)

**`TrainingWorkflowStepper`** component visualizing the exact state machine from `PROJECT_SPEC.md §16` / `DATABASE_SPEC.md §2.8`:

```
Upload → Validate → Preview → Data Quality Report → Select/Confirm Target Column
   → Preprocess → Train → Evaluate → Review Metrics → Activate Model
```

- Reuses the Upload/Preview/Quality-Report/Mapping UI from §10 (a training run starts from an already-uploaded dataset or a fresh upload inline).
- **Target column selection** is its own explicit step (dropdown of candidate binary columns detected in the dataset) — never auto-guessed silently, per `PROJECT_SPEC.md §16.1`.
- If no valid target column exists, the workflow stops at this step with the exact blocking message from `PROJECT_SPEC.md §16` ("Training requires historical outcomes...") and a clear alternative CTA ("Use the baseline model for predictions instead").
- Once training starts (`POST /api/training/jobs`), the page polls `GET /api/training/jobs/:id` and reflects live status (`queued → validating → preprocessing → training → evaluating → completed/failed`) with a step-by-step progress indicator, not just a spinner.
- **Evaluate / Review Metrics** step: full metric suite from `ML_SPEC.md §12` (accuracy, precision, recall, F1, ROC-AUC, PR-AUC, confusion matrix) rendered from `models.metrics`, plus the model-comparison context (this company model vs. the shared baseline) so the user isn't just shown numbers with no reference point.
- **Activate** step: explicit confirmation dialog (`ConfirmDialog`, §24) before calling `POST /api/models/:id/activate`, since activating changes what every future prediction on this org uses.
- Training-job history list (`GET /api/training/jobs`) shows past runs, their outcome, and links to the resulting model in `/models`.

## 12. Prediction Screens (`/predict`)

Two modes, either as tabs or sub-routes:

### 12.1 Single Prediction
- **`PredictionForm`** — input fields generated from the active model's `feature_schema` (`DATABASE_SPEC.md §2.7`) so the form always matches what the active model actually expects, rather than a hardcoded field list that could drift from the model.
- On submit (`POST /api/predictions/single`): result panel shows churn probability (with a visual gauge), predicted class, `RiskBadge`, and a "Top Reasons" ranked list pulled from `explanations.top_factors`.
- **`ShapForcePlot`** — see §12.3.
- A `422 SCHEMA_MISMATCH` response (mismatched/missing required fields against the active model) is shown as a specific, actionable inline error, not a generic failure toast.

### 12.2 Batch Prediction
- Reuses `UploadDropzone` (§10) scoped to `POST /api/predictions/batch`. Target column is not required here (matching `API.md`), but the same schema-mapping confirmation step applies.
- Small files: synchronous result. Larger files: polls `GET /api/predictions/batch/:id` (status `queued → processing → completed/failed`), showing a progress state consistent with the Training Workflow's polling pattern.
- **Prediction Summary panel:** total records, high/medium/low risk counts, predicted churn rate — computed by the backend from actual per-row results, not aggregated client-side from a partial page of data.
- **Download Results** button hits `GET /api/predictions/batch/:id/download`.

### 12.3 SHAP Visualization (shared component, used in single prediction, batch row drill-down, and Customer Detail)
- **`ShapForcePlot`** — base value → ranked feature contributions (color-coded increase/decrease of churn risk) → final predicted probability, rendered from `explanations.shap_values`/`base_value` (never templated text).
- **`ShapGlobalSummary`** — ranked mean-|SHAP| bar list, reused on Dashboard (§9) and Analytics (§14), rendered from `models.artifact_path`'s cached `global_shap.json` via the API, per `ML_SPEC.md §13`.
- Every SHAP surface carries the fixed disclaimer text from `PROJECT_SPEC.md §15`: *"This shows what the model learned from patterns in the data — it identifies correlation, not proven causation."*
- Loading state for SHAP-heavy views uses a skeleton shaped like the force plot/bar list (not a generic spinner), since SHAP computation can add noticeable latency (`ML_SPEC.md §13`'s documented performance budget).

## 13. Customer List & Detail

- **`/customers`** — `DataTable` with search (name/id), filter by risk level, sort (by risk, last prediction date), pagination — backed by `GET /api/customers`.
- **`/customers/[id]`** — profile fields from `customers.feature_data`, full prediction history for that customer (`GET /api/customers/:id`, backed by `predictions.customer_id`), each history row expandable to its `ShapForcePlot` local explanation.

## 14. Analytics (`/analytics`)

Deeper breakdowns beyond the Dashboard's summary view: segment analysis (richer cuts than the Dashboard's headline radar), feature-distribution views (reusing `ML_SPEC.md §2`'s EDA visual types — histograms, categorical churn-rate bars, correlation view), and, when more than one company model exists, a model-comparison table (metrics side by side, per `ML_SPEC.md §7`'s comparison-table requirement, surfaced to the user rather than staying developer-only).

## 15. Model Management (`/models`)

`DataTable`/card list of model versions (`GET /api/models`) — baseline + company-specific — each showing algorithm, version, key metrics, training date, active/inactive status, with Activate/Deactivate actions (behind `ConfirmDialog`) and a link into the full metrics + global SHAP view (`GET /api/models/:id`).

## 16. Reports (`/reports`)

Generate (`POST /api/reports/generate`) and list/download (`GET /api/reports`, `GET /api/reports/:id/download`) exportable summaries, per `API.md`. Report-type selection and filter UI matches whatever filter parameters `API.md §Reports` finalizes at Phase 10/12.

## 17. Settings (`/settings`)

Profile (name, email — email change flow deferred to a future phase if it requires re-verification, documented as such rather than half-built), organization info, theme preference (mirrors §3), risk thresholds shown **read-only** in V1 with a "customize thresholds — coming soon" note (`PROJECT_SPEC.md §18`/`§50`), active sessions list (future, `sessions` table already supports it).

## 18. Help & FAQ (`/help`)

- Replayable `OnboardingTour` entry point.
- Glossary of terms (same content source as the inline tooltips, §8).
- FAQ covering, at minimum, the questions in `PROJECT_SPEC.md §21`: what churn means, how to upload data, what data is required, what the probability number means, what each risk level means, what SHAP means, what company-specific training requires and why labels are mandatory.

## 19. State Coverage (binding — applies to every data-bearing view above)

Every view that renders data-dependent content implements all four states before it is considered done:

1. **Loading** — a skeleton matching the eventual layout (table-shaped skeleton for tables, chart-shaped skeleton for charts, force-plot-shaped skeleton for SHAP), not a generic spinner standing in for structured content.
2. **Empty** — explains what's missing and gives a clear next action (e.g., "No predictions yet — run your first prediction" with a button to `/predict`).
3. **Error** — a human-readable message derived from the API error envelope (`BACKEND_SPEC.md §7`), with a retry action where applicable, and the `request_id` available for support reference.
4. **Populated** — the real designed view, always sourced from a live API response (binding rule, `PROJECT_SPEC.md`).

No screen ships with sample/mock data standing in for a missing empty or populated state.

## 20. Success States, Confirmations & Notifications

- **Toasts** for transient success/failure feedback (upload succeeded, prediction complete, model activated).
- **`ConfirmDialog`** required before any destructive or high-impact action: deleting a dataset, deactivating a model, discarding an in-progress upload/training flow.
- **Inline success states** for forms (e.g., "Password updated" persists in-place rather than only flashing a toast) where the user needs durable confirmation.

## 21. Responsive Behavior

- Fully responsive from desktop down to mobile widths, matching the intent of the reference image's included mobile preview (implemented as a real responsive layout, not a separate mobile-only mock).
- **Breakpoints:** desktop (sidebar expanded), tablet (sidebar collapses to icon rail), mobile (sidebar becomes a slide-over drawer opened from the `Topbar`; KPI cards and charts stack vertically; `DataTable`s switch to a stacked-card layout per row instead of horizontal scroll where practical).
- Touch-friendly tap targets on mobile (minimum 44×44px interactive elements).

## 22. Accessibility

- Keyboard navigable throughout: full tab order, visible focus rings (token-defined, meets contrast in both themes), focus trapping inside modals/dialogs, Escape-to-close.
- WCAG AA color contrast in both themes for text and meaningful UI elements.
- Risk-level color coding always paired with text/icon, never color alone (colorblind-safe, §2).
- Charts include an accessible text alternative (e.g., sr-only summary of KPI values, table-equivalent data available for screen readers alongside Recharts SVG output).
- Semantic HTML and ARIA labeling on custom interactive components (`Sidebar`, `Tabs`, `DataTable` sort controls, `Tooltip`, `ConfirmDialog`).

## 23. Animations & Micro-interactions

Restrained and professional — motion serves comprehension, not decoration:

- Page/section transitions: brief fade/slide on route change (Framer Motion), short enough not to delay perceived load.
- Skeleton-to-content swap: cross-fade rather than an abrupt pop.
- Chart entrance: bars/donut segments animate in once on first render of populated data, not on every re-render/poll tick.
- Toast enter/exit: slide + fade, auto-dismiss with a visible timer.
- Hover/focus states: subtle elevation/border-color shift on cards and rows, immediate (no artificial delay).
- No parallax, no auto-playing decorative animation, no motion that cannot be reasonably disabled via `prefers-reduced-motion` (respected globally — animations shorten/disable when the OS setting requests it).

## 24. Component Inventory (`components/ui/` and `components/<feature>/`)

**Primitives (`components/ui/`):** `Button`, `Input`, `Select`, `Card`, `Modal`/`Dialog`, `Toast`/`ToastProvider`, `Tooltip`, `Tabs`, `Table` (base), `Skeleton`, `Badge`, `ProgressStepper`, `Gauge` (for the probability display).

**Feature components (`components/<feature>/`):** `Sidebar`, `Topbar`, `Footer`, `KpiCard`, `RiskDonutChart`, `ChurnTrendChart`, `TopDriversBarList`, `SegmentRadarChart`, `DataTable` (sortable/paginated/filterable, built on the `Table` primitive, reused across Recent Predictions/Customers/Model list/Training history), `UploadDropzone`, `DataQualityReportPanel`, `ColumnMappingPanel`, `TrainingWorkflowStepper`, `PredictionForm`, `ShapForcePlot`, `ShapGlobalSummary`, `RiskBadge`, `ConfirmDialog`, `EmptyState`, `ErrorState`, `OnboardingTour`.

## 25. Testing Strategy (frontend)

- **Component tests** (React Testing Library): `UploadDropzone` validation states, `DataTable` sorting/filtering/pagination, `PredictionForm` submission + result rendering (including the `SCHEMA_MISMATCH` error path), `RiskBadge` mapping, theme toggle persistence, `ConfirmDialog` gating a destructive action.
- **Flow-level tests:** signup → redirect to dashboard; login → protected-route access; logout → redirect + session cleared; upload → data quality report renders correctly for a known-bad fixture CSV; training workflow blocked correctly when no target column exists; batch prediction polling reaches a completed state and enables download.
- **Visual/manual QA checklist** (Phase 11): both themes, across desktop/tablet/mobile breakpoints, for every page in §7–§18.
