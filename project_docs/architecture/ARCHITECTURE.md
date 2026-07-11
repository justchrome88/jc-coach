> R02A2 canonical source: `_legacy_archive/r02a2-2026-07-11/docs/ARCHITECTURE.md`. The original is preserved byte-identically; this copy updates canonical paths only.

# Architecture

Last updated: 2026-07-11.

## Purpose

This document is a current map of the JC Coach application shape and module
boundaries. It is descriptive only: it does not establish task or release
readiness, authorize broad refactors, authorize production DB mutation, or
approve import/parser/evaluator/runtime work. Task and release routing live in
`project_control/`.

## Top-Level Shape

- `app/main.py` builds the FastAPI application, mounts `/static`, configures
  Jinja templates, adds session/security middleware, registers `/health` and
  `/robots.txt`, and includes the API and web routers.
- `app/api/routes.py` owns JSON API endpoints under `/api`.
- `app/web/routes.py` owns server-rendered pages and form posts.
- `app/services/` holds business logic for imports, Steam integration, demo
  parsing/storage, analytics, metric confidence/truth, recommendations, report
  generation, AI coach handoff/generation, auth, security and i18n.
- `app/db/session.py` owns SQLAlchemy engine/session setup, `get_db()`,
  startup `init_db()`, and the current SQLite compatibility helper.
- `app/db/models.py` owns SQLAlchemy persistence models.
- `app/templates/` contains Jinja2 pages for the landing/login/register flow,
  dashboard, stats, coach, match detail, report, upload and settings views.
- `app/static/` contains browser assets, currently CSS and chart JavaScript.
- `tests/` contains pytest coverage for service behavior, route smoke checks,
  import/parser/storage/recommendation/security behavior, project gates and
  DB/schema safety guards.

## Current Data Flow

```text
CSV/JSON uploads
  -> app.api/app.web import endpoints
  -> app.services.importer
  -> app.db.models.Match rows
  -> analytics/metric confidence/recommendations/reports/coach views

DEM uploads or inbox demos
  -> app.api/app.web demo import endpoints
  -> app.services.demo_parser and app.services.demo_storage
  -> Match plus demo artifact/detail tables
  -> analytics, match detail, coach and recommendation evidence

Steam account/share-code paths
  -> app.web/app.api Steam routes
  -> app.services.steam_integration
  -> optional app.services.steam_demo_downloader and demo parser path
  -> ImportJob, SteamAccount, Match and parser artifact rows
  -> import overview, settings, analytics and recommendation evidence

Existing DB facts
  -> app.services.match_queries/playable_match_select
  -> analytics, aim stats, mistake detection, metric confidence/truth
  -> recommendations, reports and AI coach payloads
  -> JSON API responses or Jinja templates
```

AI and recommendations must consume persisted or derived deterministic facts.
They must not invent parser data, playlist mode, match dates or hard metric
confidence. Low-confidence metrics must remain caveated. Source trust,
sample-size thresholds, mixed-source aggregation and period comparison
semantics are governed by `project_docs/metrics/METRICS.md`.

CS2 domain claims are bounded by `project_docs/product/CS2_DOMAIN_CONTRACT.md`. Economy,
positioning and clutch models are unavailable; side metrics are display-only;
map labels are source-provided until a canonical map registry is accepted.
Validated same-round five-second trade opportunities and traded/untraded death
rates can support bounded aggregate patterns, but not exact position, spacing,
angle, rotation, crosshair placement or individual counterfactual instructions. Coach, report,
recommendation and AI surfaces must keep these source limitations visible
instead of implying unsupported certainty. Mixed CSV, JSON, demo, Steam or
future FACEIT facts must not be combined into hard advice unless source trust,
metric reliability, sample thresholds and comparison-window rules all pass.

## Route Layers

### Current Route Boundary Inventory

This inventory describes the current route surface from `app/main.py`,
`app/api/routes.py` and `app/web/routes.py`. It is descriptive only. Route
restructuring, authentication boundary changes, request/response contract
changes or mutation semantic changes require explicit future task scope.

Mutation classes used below:

- `read`: returns health, rendered pages or existing DB/config/filesystem facts.
- `session-write`: changes browser session or cookies.
- `db-write`: writes persisted application rows.
- `artifact-write`: writes a generated handoff, report, manifest or similar
  persisted artifact.
- `import-parser-write`: imports CSV/JSON/DEM data or runs parser-backed
  import logic.
- `steam-import-write`: queues, runs or repairs Steam/Valve import work.

Sensitive classes used below:

- `public`: currently allowed without an authenticated owner session.
- `owner`: requires an authenticated owner session, or for `/api/*` a valid API
  bearer token according to `app/main.py` middleware.
- `auth-sensitive`: login, registration, logout, CSRF, session or owner-linking
  behavior.
- `import-parser-sensitive`: CSV/JSON/DEM import, parser or inbox import path.
- `steam-sensitive`: Steam OpenID, share-code, queued import or demo-download
  path.
- `recommendation-sensitive`: tracked recommendation state or evaluation
  evidence path.
- `report-ai-sensitive`: persistent coach report, AI handoff/result or provider
  generation path.
- `db-risk`: route can write DB rows when pointed at the production DB.
- `artifact-risk`: route can write a persistent non-DB artifact.

Validation responsibility classes used below:

- `middleware-owned`: auth, API token, CSRF, rate-limit and public-path checks
  enforced before route handlers.
- `framework-owned`: FastAPI/Starlette request parsing and declared type
  binding for path/query/form/file parameters.
- `route-owned`: explicit handler checks or exception translation visible in
  `app/api/routes.py` or `app/web/routes.py`.
- `service-owned`: validation delegated to service functions, usually reported
  through `ValueError`, domain exceptions or service result payloads.
- `implicit/follow-up`: behavior currently accepted by broad defaults, free
  text, redirects or unenumerated strings. Treat these as candidates for future
  focused tests or stricter validation, not as complete validation coverage.

### Endpoint Safety Classes And Review Expectations

| Endpoint class | Current route groups | Required future review/check focus |
|---|---|---|
| `read-only` | Health/robots/static, public page reads, owner page reads, analytics/matches/recommendation/report/AI/storage overview reads. | Confirm no persistent side effects, owner/API auth where applicable, and service-owned caveats for parser, metric confidence, recommendations and AI payloads. Focused route smoke tests are usually enough unless service behavior changes. |
| `write/mutation` | Login/register/logout, locale cookie, settings writes, storage manifest, report generation, AI handoff/result/generate, recommendation status/extend/restart. | Require auth/owner and CSRF/API-token checks, focused side-effect tests and explicit no-production-DB-touch or DB SHA evidence according to task risk. |
| `import/parser/evaluator-risk` | CSV/JSON/DEM upload, inbox demo import, Steam share-code/import job/run-queued/pull-all paths. | Require explicit authorization before running import/parser work, isolated fixture or mocked tests, no production parser/import/evaluator jobs unless the task card explicitly permits them. |
| `auth/owner-sensitive` | Login/register/logout, Steam callback/linking, all owner web routes and all `/api/*` routes. | Require owner-boundary, non-owner rejection, API-token/session split and CSRF tests when changed. Steam callback remains public at middleware level but handler-gated by current owner session before linking. |
| `DB/schema-risk` | Any route that calls services writing users, settings, Steam accounts/jobs, matches/imports, recommendations, coach reports or storage manifests. | Route writes are not schema changes by themselves. Schema/model/startup/migration/baseline/copy work remains approval-required and outside ordinary route documentation tasks. |
| `unknown` | Any route or service side effect not proven by handler code plus canonical docs. | Mark as follow-up. Do not assume safe checks or complete validation without targeted evidence. |

### Route-Level Validation Inventory

| Route area | Current validation/auth behavior | Conservative follow-up candidates |
|---|---|---|
| Middleware boundary | `app/main.py` enforces `/api/*` owner session or configured bearer token, CSRF for browser-backed writes, owner redirects for non-public web routes, public-path exceptions and mutation rate-limit buckets. | Add/maintain focused tests for API token vs browser CSRF paths, public path exceptions, non-owner session rejection and mutation rate-limit buckets when these boundaries change. |
| Public auth/session routes | Login/register inputs are form-bound; auth/register services validate credentials and owner policy; logout clears session; locale is normalized through `normalize_locale()`. | Stronger route-level documentation/tests for invalid locale redirects and public POST CSRF coverage if behavior changes. |
| Web reads and filters | Matches/stats pages use FastAPI type binding for integer pagination and local date parsing/filtering. Match detail redirects when the match is missing or not playable. | Invalid date strings, unrecognized sort/direction/filter values and page/per-page edge cases are practical follow-up candidates for explicit route validation or tests. |
| API import/parser routes | Upload fields are framework-bound; `/api/import/demo` checks `.dem`; parser failures map to `422`; JSON/service validation failures map to `400` where caught. | Explicit file size/content-type expectations, inbox filename safety at route boundary and parser error shape tests remain follow-up candidates unless service tests already cover the behavior. |
| Web upload/import routes | Upload extension selects DEM/JSON/CSV-like import path; parser errors render messages; inbox demo import delegates filename validation to service code. | Invalid file extension/content handling and web status/message conventions are implicit and should be tested before behavior is treated as locked. |
| Recommendations | Path IDs/categories and form/query values are type-bound; status/extend/restart validation is service-owned and surfaced as `400` in API routes or redirect messages in web routes. | Explicit route constraints for allowed statuses/categories and min/max extension counts are follow-up candidates. |
| Reports and AI coach | Latest resources return `404` on JSON API reads where explicitly checked; generation/result save delegates provider/runtime/content validation to services. | Free-text report/AI result input size/format expectations and provider failure response conventions need focused tests if changed. |
| Steam/import jobs | Share-code parsing, auth-code validation, job state checks and queue/run behavior are service-owned; API routes map selected `ValueError`s to `400`, web routes redirect with messages. | Stronger route-level tests for malformed share codes, wrong job IDs, queued-job state transitions and API-token access should precede any route behavior change. |
| Storage manifest | Auth/CSRF comes from middleware; write behavior delegates to `write_demo_storage_manifest()`. | Tests should confirm manifest writes use isolated paths and do not touch raw demos; delete/move/compress behavior remains forbidden without storage scope. |

#### Application And Public Routes

| Route | Boundary | Mutation class | Sensitive class |
|---|---|---|---|
| `GET /health` | Public JSON health response from `app/main.py`. | `read` | `public` |
| `GET /robots.txt` | Public robots policy from `app/main.py`. | `read` | `public` |
| `GET /static/*` | Static files mounted by `app/main.py`. | `read` | `public` |
| `GET /` | Landing page, redirects authenticated users to `/dashboard`. | `read` | `public` |
| `GET /login`, `POST /login` | Login page and credential submission. | `read`, `session-write` | `public`, `auth-sensitive` |
| `GET /register`, `POST /register` | Registration page and owner/user creation flow. | `read`, `db-write`, `session-write` | `public`, `auth-sensitive`, `db-risk` |
| `POST /logout` | Clears the browser session. | `session-write` | `owner`, `auth-sensitive` |
| `GET /language/{locale}` | Sets locale cookie and redirects back. | `session-write` | `public` |
| `GET /auth/steam/callback` | Steam OpenID callback. It is public at middleware level but requires a current owner session in the handler before linking. | `db-write` | `public`, `auth-sensitive`, `steam-sensitive`, `db-risk` |

#### Web Read Routes

| Route | Boundary | Mutation class | Sensitive class |
|---|---|---|---|
| `GET /dashboard` | Owner dashboard built from playable matches, analytics, aim stats and recommendation progress. | `read` | `owner` |
| `GET /stats` | Owner stats page with range/date filters and metric confidence context. | `read` | `owner` |
| `GET /coach` | Coach overview from analytics, mistakes, recommendation progress, reports and AI result history. | `read` | `owner`, `recommendation-sensitive`, `report-ai-sensitive` |
| `GET /upload` | Upload page and inbox demo listing. | `read` | `owner`, `import-parser-sensitive` |
| `GET /settings/imports` | Steam/import settings page and import job overview. | `read` | `owner`, `steam-sensitive` |
| `GET /settings/storage` | Demo storage report page. | `read` | `owner` |
| `GET /auth/steam` | Redirects owner to Steam OpenID login URL. | `read` | `owner`, `auth-sensitive`, `steam-sensitive` |
| `GET /matches` | Match list with filters, pagination, evaluation status and date-truth labels. | `read` | `owner` |
| `GET /matches/{match_id}` | Match detail with parser summary, mistake and recommendation evaluation context. | `read` | `owner`, `import-parser-sensitive`, `recommendation-sensitive` |
| `GET /report` | Latest generated coach report page. | `read` | `owner`, `report-ai-sensitive` |

#### Web Mutation Routes

| Route | Boundary | Mutation class | Sensitive class |
|---|---|---|---|
| `POST /settings/storage/manifest` | Writes demo storage manifest through `write_demo_storage_manifest()`. | `artifact-write` | `owner`, `artifact-risk` |
| `POST /settings/imports/steam-web-api-key` | Stores Steam Web API key in app settings. | `db-write` | `owner`, `steam-sensitive`, `db-risk` |
| `POST /settings/imports/steam/{steam_account_id}/auth-code` | Stores match auth/latest share-code values for a Steam account. | `db-write` | `owner`, `steam-sensitive`, `db-risk` |
| `POST /settings/imports/steam/{steam_account_id}/share-code` | Imports or queues a Steam share-code demo path. | `steam-import-write` | `owner`, `steam-sensitive`, `import-parser-sensitive`, `db-risk` |
| `POST /settings/imports/steam/{steam_account_id}/sync` | Queues Steam match-history sync. | `steam-import-write` | `owner`, `steam-sensitive`, `db-risk` |
| `POST /settings/imports/jobs/{job_id}/run` | Runs one queued Steam import job. | `steam-import-write` | `owner`, `steam-sensitive`, `db-risk` |
| `POST /settings/imports/run-queued` | Processes queued Steam import jobs. | `steam-import-write` | `owner`, `steam-sensitive`, `db-risk` |
| `POST /settings/imports/pull-all` | Queues all-match Steam import and may start a background task. | `steam-import-write` | `owner`, `steam-sensitive`, `db-risk` |
| `POST /settings/imports/clear-demo-errors` | Clears old Steam demo download errors. | `db-write` | `owner`, `steam-sensitive`, `db-risk` |
| `POST /upload` | Imports uploaded `.dem`, `.json` or CSV-like content. | `import-parser-write` | `owner`, `import-parser-sensitive`, `db-risk` |
| `POST /upload/server-demo` | Imports a named inbox demo. | `import-parser-write` | `owner`, `import-parser-sensitive`, `db-risk` |
| `POST /report/generate` | Generates and persists a coach report. | `db-write`, `artifact-write` | `owner`, `report-ai-sensitive`, `db-risk` |
| `POST /coach/ai-handoff` | Creates an AI coach handoff artifact. | `artifact-write` | `owner`, `report-ai-sensitive`, `artifact-risk` |
| `POST /coach/ai-result` | Saves submitted AI coach markdown as a persisted result. | `db-write` | `owner`, `report-ai-sensitive`, `db-risk` |
| `POST /coach/ai-generate` | Calls configured AI provider and persists generated coach result. | `db-write`, `artifact-write` | `owner`, `report-ai-sensitive`, `db-risk` |
| `POST /coach/recommendations/{recommendation_id}/status` | Updates tracked recommendation status. | `db-write` | `owner`, `recommendation-sensitive`, `db-risk` |
| `POST /coach/recommendations/{recommendation_id}/extend` | Extends tracked recommendation target matches. | `db-write` | `owner`, `recommendation-sensitive`, `db-risk` |
| `POST /coach/recommendations/category/{category}/restart` | Restarts a tracked recommendation category. | `db-write` | `owner`, `recommendation-sensitive`, `db-risk` |

#### API Route Groups

All `/api/*` routes are authenticated by middleware through either a current
owner session or a configured `Authorization: Bearer <token>` API token. API
state-changing methods are logged as API state changes. When a browser session
is used without the API token, API writes also require the current CSRF token.

| Route group | Routes | Mutation class | Sensitive class |
|---|---|---|---|
| Matches | `GET /api/matches` | `read` | `owner` |
| Imports | `POST /api/import/csv`, `POST /api/import/json`, `POST /api/import/demo`, `GET /api/import/demo/inbox`, `POST /api/import/demo/inbox`, `GET /api/import/jobs` | `read`, `import-parser-write` | `owner`, `import-parser-sensitive`, `db-risk` for write routes |
| Analytics | `GET /api/analytics/summary`, `GET /api/analytics/aim` | `read` | `owner` |
| Recommendations | `GET /api/recommendations/active`, `GET /api/recommendations`, `GET /api/recommendations/history`, `GET /api/recommendations/categories`, `POST /api/recommendations/{recommendation_id}/status`, `POST /api/recommendations/{recommendation_id}/extend`, `POST /api/recommendations/categories/{category}/restart` | `read`, `db-write` | `owner`, `recommendation-sensitive`, `db-risk` for write routes |
| Reports | `POST /api/reports/generate`, `GET /api/reports/latest` | `read`, `db-write`, `artifact-write` | `owner`, `report-ai-sensitive`, `db-risk` for generate |
| AI coach | `GET /api/coach/ai/payload`, `POST /api/coach/ai/handoff`, `GET /api/coach/ai/handoff/latest`, `GET /api/coach/ai/provider/health`, `POST /api/coach/ai/generate`, `POST /api/coach/ai/result`, `GET /api/coach/ai/result/latest`, `GET /api/coach/ai/results` | `read`, `db-write`, `artifact-write` | `owner`, `report-ai-sensitive`, `db-risk` for persisted result/generate, `artifact-risk` for handoff |
| Steam/import | `GET /api/steam/login-url`, `GET /api/steam/accounts`, `POST /api/steam/import/share-code`, `POST /api/steam/import/jobs/{job_id}/run`, `POST /api/steam/import/jobs/run-queued`, `POST /api/steam/import/all`, `GET /api/steam/import/overview`, `GET /api/steam/demo-downloader/status` | `read`, `steam-import-write`, `db-write` | `owner`, `steam-sensitive`, `db-risk` for write/import routes |
| Demo storage | `GET /api/storage/demos`, `POST /api/storage/demos/manifest` | `read`, `artifact-write` | `owner`, `artifact-risk` for manifest |

### `app/main.py`

`app/main.py` is the app composition layer. It may wire routers, middleware,
template context and static files. It should not absorb product workflows that
belong in services.

Sensitive boundary:

- `lifespan()` calls `init_db()` on startup. Startup schema behavior is
  schema-sensitive work and must not be changed without explicit schema scope.
- The optional stale Steam import repair path is runtime/import-sensitive and
  must not be changed or enabled through unrelated work.
- Security middleware opens short-lived DB sessions for auth checks and logs
  state-changing requests. Route-specific business behavior should stay out of
  the middleware.

### `app/api`

`app/api/routes.py` exposes machine-oriented JSON routes. It should:

- validate HTTP inputs and convert service exceptions to HTTP errors;
- obtain DB sessions through `Depends(get_db)` for request-scoped work;
- call service modules for imports, analytics, recommendations, reports,
  Steam work, storage reports and AI coach operations;
- serialize service/model results into simple dictionaries.

It should not:

- embed durable product policy when a service already owns that policy;
- perform direct schema changes;
- perform filesystem cleanup or Steam/parser/evaluator work outside explicit
  task scope;
- bypass service-level metric confidence, storage guard or recommendation
  safety logic.

Mutation-heavy API paths include upload/import endpoints, recommendation status
updates, report generation, AI result save/generate, Steam import/job endpoints
and demo storage manifest writing.

### `app/web`

`app/web/routes.py` exposes browser pages and form posts. It should:

- build Jinja view models from service outputs;
- handle redirects, forms and user-visible messages;
- keep browser-specific selection/filtering close to template needs;
- call services for durable operations.

It should not:

- duplicate API/service business rules for imports, parser facts,
  recommendations or metric confidence;
- make cross-layer schema/runtime/import changes without explicit scope;
- treat page labels as authorization to make unsupported CS2 claims.

Mutation-heavy web paths include login/register/logout, settings writes,
Steam linking/auth-code/share-code/sync/import actions, uploads, server-demo
imports, storage manifest writing, report generation, AI handoff/result/generate
actions and recommendation status/extend/restart actions.

## Service Layer

Services own product behavior and reusable workflows:

- Import and parser: `importer.py`, `demo_parser.py`, `demo_storage.py`,
  `demo_retention.py`.
- Steam and storage guard: `steam_integration.py`,
  `steam_demo_downloader.py`, `steam_match_metadata.py`,
  `steam_storage_guard.py`.
- Analytics and metric safety: `analytics.py`, `aim_stats.py`,
  `metric_confidence.py`, `metric_truth.py`, `mistake_detection.py`,
  `match_queries.py`.
- Recommendations and reports: `recommendation_tracking.py`,
  `report_generator.py`, `coach_rules.py`.
- AI coach: `ai_coach.py`, `ai_validator.py`.
- User/app/security support: `auth.py`, `app_settings.py`, `security.py`,
  `i18n.py`.

Expected boundary:

- Add or change product logic in the service that owns the behavior, then keep
  API/web routes as thin orchestration and serialization layers.
- Keep deterministic fact extraction, confidence handling and caveats in
  services, not templates.
- Keep source-trust, sample-size, aggregation and period-comparison caveats
  attached to service outputs that feed recommendations, reports, API payloads
  or AI coach handoffs.
- Keep provider calls and payload construction behind service functions.
- Add tests near the changed service behavior before relying on route tests.

Sensitive services:

- `steam_integration.py` and `steam_demo_downloader.py` touch live Steam/Valve
  import paths, import jobs, demo download state, storage budgets and external
  helper execution. Do not run or change these paths without explicit scope.
  `ImportJob.status` remains coarse; service behavior, UI/API labels and task
  reports must use `result_json` for detailed outcome, retryability and safety
  evidence.
- `demo_parser.py` reads/stores DEM-derived facts and parser artifacts. Parser
  jobs on production data require explicit authorization.
- `recommendation_tracking.py` writes recommendation evaluations and progress.
  Legacy recommendation and metric-confidence rules in `AGENTS.md` apply.
- `report_generator.py` and `ai_coach.py` can create persistent reports or
  handoff files. Do not generate persistent app reports unless a task explicitly
  authorizes that side effect.
- `demo_storage.py`, `demo_retention.py` and `steam_storage_guard.py` touch
  demo-file accounting and retention boundaries. Do not delete, move or
  compress raw demos without explicit storage scope.
- Durable import workers, retry ledgers, queue runners, stale-job repair and
  import cap changes are not general service refactors. They require explicit
  import-worker/retry/cap scope, safety evidence and, when persistence changes
  are needed, separate schema/data authorization.

## DB, Session And Model Layer

`app/db/models.py` is the persistence model layer. Current primary tables
cover matches, demo parser artifacts/details, coach reports, recommendations,
recommendation evaluations, users, Steam accounts, import jobs and app
settings.

`app/db/session.py` owns:

- `Base`, engine and `SessionLocal`;
- `get_db()` request/session dependency;
- `init_db()`, including current `Base.metadata.create_all()` startup behavior;
- the current SQLite compatibility helper for known historical columns.

Expected boundary:

- Models define stored shape and relationships, not coach policy.
- Services decide how rows are interpreted, filtered, caveated and mutated.
- Routes should use `get_db()` unless a background task or middleware needs a
  short-lived explicit `SessionLocal()` session.
- Schema, migration/baseline, startup schema behavior and copied-DB work are
  separate approval-required scopes under `AGENTS.md`.

Production-DB-sensitive boundary:

- `data/cs2_coach.db` is the production DB.
- Read-only evidence collection is distinct from mutation.
- DB/schema-risk tasks that do not touch production DB must say so explicitly.
- Production DB mutation requires explicit task authorization, backup evidence
  and before/after SHA evidence.

## Templates And Static Assets

Templates under `app/templates/` render browser workflows. They should consume
view models passed by `app/web/routes.py` and avoid embedding durable product
policy that belongs in services.

Static files under `app/static/` are mounted at `/static`. Browser-only styling
or display behavior belongs here when it does not change server-side product
logic.

When adding UI:

- put route/view-model orchestration in `app/web`;
- put reusable product logic in `app/services`;
- put persistent data shape in `app/db` only with explicit schema scope;
- add route smoke or service tests in `tests/` as appropriate.

## Tests

Tests live under `tests/`. `tests/conftest.py` sets `APP_ENV=test`, routes test
runtime paths to temporary locations and guards against using the production DB
for pytest.

Expected test ownership:

- service behavior changes should have focused service tests;
- web/API behavior changes should have route or smoke tests after service tests
  cover the underlying rule;
- project-governance or gate behavior belongs in project gate tests;
- DB/schema safety behavior belongs in focused DB/schema guard tests and must
  respect the schema approval policy.

Do not use pytest, Ruff or the local quality gate for a docs-only task unless
code, scripts or tests changed despite the intended scope.

## Safe Architecture Rules For Future Agents

Endpoint changes require tests at the same boundary that changes:

- path, method, auth, CSRF/API-token behavior, status code, redirect target,
  request input or representative response shape changes require focused
  endpoint contract tests;
- service behavior changes require service tests first, with route tests only
  for HTTP translation, auth and serialization;
- DB/session/model, startup schema behavior, migration/baseline or copied-DB
  changes require explicit schema scope before edits and DB/SHA evidence under
  `AGENTS.md`;
- import, parser, Steam, evaluator or manual-evaluator behavior requires
  explicit PM/user scope before live work, and tests must use isolated fixtures
  or mocks rather than production data or jobs;
- import cap raises remain blocked until worker/retry/result safety is accepted
  and a separate cap-change WP authorizes the change;
- persistent report, AI handoff/result and demo-storage manifest routes must
  prove temp-path isolation in tests or declare no artifact write;
- route or service work must not add playlist, metric-confidence,
  recommendation or AI claims beyond accepted persisted evidence and caveats.

## Read/Write And Sensitive Path Summary

Read-oriented paths:

- `/dashboard`, `/stats`, `/coach`, `/matches`, `/matches/{match_id}`,
  `/report` and corresponding API reads mostly consume DB facts through
  services and render JSON/templates.
- Analytics, aim stats, metric confidence/truth, mistake detection and match
  queries should stay deterministic and caveated.

Write/mutation paths:

- imports from CSV/JSON/DEM, Steam account linking/settings, Steam sync/import
  jobs, demo storage manifests, report generation, AI result persistence,
  recommendation status/extend/restart and auth/settings updates.

Import/parser/evaluator-sensitive areas:

- Steam routes and `app.services.steam_*`;
- DEM import routes and `app.services.demo_parser`;
- recommendation evaluation paths in `app.services.recommendation_tracking`;
- report/AI generation paths when they create persistent artifacts.

Production-DB-sensitive areas:

- any code path using the default `DATABASE_URL` from `app/config.py`;
- `app/db/session.py` startup behavior;
- service functions that call `db.add()`, `db.commit()`, `db.delete()` or
  execute write statements;
- scripts or tests that could point at `data/cs2_coach.db`.

## Common Change Placement

- New JSON endpoint: add request/response orchestration in `app/api/routes.py`,
  reusable behavior in `app/services`, and tests in `tests/`.
- New browser page/form: add route/view model in `app/web/routes.py`, template
  in `app/templates`, static assets in `app/static` if needed, reusable logic
  in `app/services`, and route/service tests in `tests/`.
- New metric or caveat: update metric truth/confidence or analytics services
  first; update templates/API serialization only after the service contract is
  explicit.
- New import/parser behavior: work in the owning import/parser/Steam service
  under explicit authorization, with storage/DB safety evidence as required.
- New stored field/table: this is schema scope. Do not make it through a
  general product task.
- New report or AI behavior: keep payload/fact assembly deterministic in
  services and preserve validator/caveat boundaries.

## Supporting Docs

- API contracts: `project_docs/architecture/API_CONTRACTS.md`
- Steam: `project_docs/operations/STEAM_IMPORT.md`
- AI: `project_docs/product/AI_COACH.md`
- Metrics: `project_docs/metrics/METRICS.md`
- Recommendations: `project_docs/product/RECOMMENDATIONS.md`
- Security: `project_docs/operations/SECURITY.md`
