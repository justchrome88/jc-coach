# Architecture

Last updated: 2026-07-07.

## Purpose

This document is a current map of the JC Coach application shape and module
boundaries. It is descriptive only: it does not mark foundation readiness as
complete, authorize broad refactors, authorize production DB mutation, or
approve import/parser/evaluator/runtime work.

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
confidence. Low-confidence metrics must remain caveated.

## Route Layers

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
- Keep provider calls and payload construction behind service functions.
- Add tests near the changed service behavior before relying on route tests.

Sensitive services:

- `steam_integration.py` and `steam_demo_downloader.py` touch live Steam/Valve
  import paths, import jobs, demo download state, storage budgets and external
  helper execution. Do not run or change these paths without explicit scope.
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

- Steam: `docs/STEAM_IMPORT.md`
- AI: `docs/AI_COACH.md`
- Metrics: `docs/METRICS.md`
- Recommendations: `docs/RECOMMENDATIONS.md`
- Security: `docs/SECURITY.md`
