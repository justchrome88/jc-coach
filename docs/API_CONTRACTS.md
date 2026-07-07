# API Contracts

Last updated: 2026-07-07.

## Purpose

This document inventories the current core API and route contracts from
`app/main.py`, `app/api/routes.py` and the public/owner web route boundary in
`app/web/routes.py`. It is descriptive, not an API versioning guarantee. Unknown
or service-owned details are marked conservatively.

Changing endpoint paths, methods, authentication expectations, request inputs,
response shapes or mutation semantics requires explicit future task scope.

## Common Contract Notes

- `GET /health`, `GET /robots.txt`, `/static/*`, `/`, `/login`, `/register`,
  `/language/{locale}` and `GET /auth/steam/callback` are public at middleware
  level.
- Non-public web routes require an authenticated owner session and redirect to
  `/login` when unauthenticated.
- `/api/*` routes require either an authenticated owner session or a configured
  `Authorization: Bearer <token>` API token.
- Browser/session-backed state-changing requests require CSRF validation.
  `/api/*` write requests using an API token do not rely on the browser CSRF
  path.
- API validation errors are generally `400`, parser failures can be `422`, and
  missing latest resources can be `404` where the handler explicitly raises
  those responses. Other service exceptions are not documented here as stable
  contracts.
- Response field summaries reflect current route serialization, not a complete
  schema promise.

Mutation classes:

- `read`: no intended persistent mutation.
- `session-write`: browser session or cookie write.
- `db-write`: persistent database write.
- `artifact-write`: persistent non-DB artifact write such as a handoff or
  manifest.
- `import-parser-write`: CSV/JSON/DEM import or parser-backed import.
- `steam-import-write`: Steam/Valve import queue or run path.

## Public And Web Boundary Contracts

| Method | Path | Auth/owner expectation | Request/input summary | Response/output summary | Mutation/read class |
|---|---|---|---|---|---|
| `GET` | `/health` | Public. | None. | JSON `{"status": "ok"}`. | `read` |
| `GET` | `/robots.txt` | Public. | None. | Plain text robots policy disallowing crawling. | `read` |
| `GET` | `/` | Public. | Session may affect redirect. | Landing template or redirect to `/dashboard`. | `read` |
| `GET` | `/login` | Public. | Optional `message`. | Login template or redirect to `/dashboard`. | `read` |
| `POST` | `/login` | Public with CSRF. | Form `email`, `password`. | Redirect to `/dashboard` on success or login template `400` on failure. | `session-write` |
| `GET` | `/register` | Public. | Optional `message`. | Register template or redirect to `/dashboard`. | `read` |
| `POST` | `/register` | Public with CSRF. | Form `email`, `password`, optional `display_name`. | Creates user, logs in, redirects to `/dashboard`; template `400` for validation failure. | `db-write`, `session-write` |
| `POST` | `/logout` | Owner session with CSRF. | None. | Clears session and redirects to `/`. | `session-write` |
| `GET` | `/language/{locale}` | Public. | Path `locale`, optional referer header. | Sets locale cookie and redirects back or `/`. | `session-write` |
| `GET` | `/auth/steam/callback` | Public at middleware level, but handler requires current owner session before linking. | Steam OpenID query parameters. | Redirects to import settings with success or error message. | `db-write` when link succeeds |

Owner web pages and form posts are inventoried in `docs/ARCHITECTURE.md`.
Their browser contract is template/redirect oriented rather than JSON oriented.

## JSON API Contract Inventory

### Matches And Analytics

| Method | Path | Auth/owner expectation | Request/input summary | Response/output summary | Mutation/read class |
|---|---|---|---|---|---|
| `GET` | `/api/matches` | Owner session or API token. | None. | List of match dictionaries from playable matches. Fields include IDs, source, played date/source, map/mode/result, score and current metrics such as kills, deaths, ADR, KAST and utility values. | `read` |
| `GET` | `/api/analytics/summary` | Owner session or API token. | None. | Object with `summary`, `comparison` and `map_stats` from analytics services. Exact nested schema is service-owned. | `read` |
| `GET` | `/api/analytics/aim` | Owner session or API token. | None. | Aim profile object from `get_aim_profile()`. Exact nested schema is service-owned. | `read` |

### Imports And Demo Parser

| Method | Path | Auth/owner expectation | Request/input summary | Response/output summary | Mutation/read class |
|---|---|---|---|---|---|
| `POST` | `/api/import/csv` | Owner session plus CSRF, or API token. | Multipart file upload. | `{"ok": true, ...result}` from `import_csv()`, currently including import counts. | `import-parser-write`, `db-write` |
| `POST` | `/api/import/json` | Owner session plus CSRF, or API token. | Multipart file upload. | `{"ok": true, ...result}` from `import_json()`; invalid JSON/data can return `400`. | `import-parser-write`, `db-write` |
| `POST` | `/api/import/demo` | Owner session plus CSRF, or API token. | Multipart `.dem` file and optional `player_identifier` query/form value as accepted by FastAPI. | `{"ok": true, ...result}` from `import_demo_file()`; non-`.dem` returns `400`, parser failure returns `422`. | `import-parser-write`, `db-write` |
| `GET` | `/api/import/demo/inbox` | Owner session or API token. | None. | `{"files": [...]}` from `list_inbox_demos()`. File item schema is service-owned. | `read` |
| `POST` | `/api/import/demo/inbox` | Owner session plus CSRF, or API token. | `filename` and optional `player_identifier` parameters. | `{"ok": true, ...result}` from `import_inbox_demo()`; parser failure returns `422`. | `import-parser-write`, `db-write` |
| `GET` | `/api/import/jobs` | Owner session or API token. | None. | List of serialized import jobs with ID, provider, job type, status, timestamps and error message. | `read` |

### Recommendations

| Method | Path | Auth/owner expectation | Request/input summary | Response/output summary | Mutation/read class |
|---|---|---|---|---|---|
| `GET` | `/api/recommendations/active` | Owner session or API token. | None. | Active recommendation progress with ID, title, status, health, baseline, target, counts, progress score, match counts and summary. Returns `404` when absent. | `read` |
| `GET` | `/api/recommendations` | Owner session or API token. | None. | List of recommendation progress objects with category, status, health, baseline/target, counts, progress score and summary. | `read` |
| `GET` | `/api/recommendations/history` | Owner session or API token. | None. | List of recommendation history rows with ID, category, title, status, priority, start/end timestamps and period match counts. | `read` |
| `GET` | `/api/recommendations/categories` | Owner session or API token. | None. | Category summary list from `recommendation_category_summary()`. Exact item schema is service-owned. | `read` |
| `POST` | `/api/recommendations/{recommendation_id}/status` | Owner session plus CSRF, or API token. | Path `recommendation_id`; parameter `status`. | `{"ok": true, "id": ..., "status": ...}` or `400` for service validation failure. | `db-write` |
| `POST` | `/api/recommendations/{recommendation_id}/extend` | Owner session plus CSRF, or API token. | Path `recommendation_id`; optional `additional_matches` default `5`. | `{"ok": true, "id": ..., "target_period_matches": ...}` or `400`. | `db-write` |
| `POST` | `/api/recommendations/categories/{category}/restart` | Owner session plus CSRF, or API token. | Path `category`. | `{"ok": true, "id": ..., "category": ..., "status": ...}` or `400`. | `db-write` |

### Reports And AI Coach

| Method | Path | Auth/owner expectation | Request/input summary | Response/output summary | Mutation/read class |
|---|---|---|---|---|---|
| `POST` | `/api/reports/generate` | Owner session plus CSRF, or API token. | None. | `{"ok": true, "id": ..., "matches_count": ..., "created_at": ...}`. | `db-write`, `artifact-write` |
| `GET` | `/api/reports/latest` | Owner session or API token. | None. | Latest report fields: ID, period start/end, match count, markdown and creation timestamp. Returns `404` when absent. | `read` |
| `GET` | `/api/coach/ai/payload` | Owner session or API token. | None. | AI coach payload from `build_ai_coach_payload()`. Exact nested schema is service-owned. | `read` |
| `POST` | `/api/coach/ai/handoff` | Owner session plus CSRF, or API token. | None. | `{"ok": true, ...handoff}` from `prepare_ai_coach_handoff()`. Handoff schema/path details are service-owned. | `artifact-write` |
| `GET` | `/api/coach/ai/handoff/latest` | Owner session or API token. | None. | Latest handoff object from `latest_ai_handoff()` or `404` when absent. | `read` |
| `GET` | `/api/coach/ai/provider/health` | Owner session or API token. | None. | Provider health object from `ai_provider_health()`. | `read` |
| `POST` | `/api/coach/ai/generate` | Owner session plus CSRF, or API token. | None. | `{"ok": true, "id": ..., "created_at": ..., "source_ref": ...}`; service runtime errors return `400`. | `db-write`, `artifact-write` |
| `POST` | `/api/coach/ai/result` | Owner session plus CSRF, or API token. | Parameters `report_markdown` and optional `source_ref`. | `{"ok": true, "id": ..., "created_at": ...}` or `400` for validation failure. | `db-write` |
| `GET` | `/api/coach/ai/result/latest` | Owner session or API token. | None. | Serialized latest AI coach report or `404` when absent. | `read` |
| `GET` | `/api/coach/ai/results` | Owner session or API token. | Optional `limit`, clamped to `1..50`, default `10`. | List of serialized AI coach reports. | `read` |

### Steam And Import Jobs

| Method | Path | Auth/owner expectation | Request/input summary | Response/output summary | Mutation/read class |
|---|---|---|---|---|---|
| `GET` | `/api/steam/login-url` | Owner session or API token. | None. | `{"url": ...}` from `steam_login_url()`. | `read` |
| `GET` | `/api/steam/accounts` | Owner session or API token. | None. | List of Steam accounts with ID, Steam ID, persona name, sync flag, last sync timestamp and auth-code presence flag. | `read` |
| `POST` | `/api/steam/import/share-code` | Owner session plus CSRF, or API token. | Parameter `share_code`. | Creates queued share-code import job and returns `{"ok": true, "job_id": ..., "status": ...}` or `400`. | `steam-import-write`, `db-write` |
| `POST` | `/api/steam/import/jobs/{job_id}/run` | Owner session plus CSRF, or API token. | Path `job_id`. | Runs/syncs job and returns `{"ok": result.status == "succeeded", ...result}` or `400`. Result schema is service-owned. | `steam-import-write`, `db-write` |
| `POST` | `/api/steam/import/jobs/run-queued` | Owner session plus CSRF, or API token. | None. | `{"ok": all succeeded, "processed": count, "results": [...]}`. Result item schema is service-owned. | `steam-import-write`, `db-write` |
| `POST` | `/api/steam/import/all` | Owner session plus CSRF, or API token. | None. | Queues all-match import and may start background task. Returns `ok`, `job_id`, `status` and progress message. | `steam-import-write`, `db-write` |
| `GET` | `/api/steam/import/overview` | Owner session or API token. | None. | Import overview object plus serialized `current_job` or `null`. Exact overview fields are service-owned. | `read` |
| `GET` | `/api/steam/demo-downloader/status` | Owner session or API token. | None. | `{"configured": true|false}`. | `read` |

### Demo Storage

| Method | Path | Auth/owner expectation | Request/input summary | Response/output summary | Mutation/read class |
|---|---|---|---|---|---|
| `GET` | `/api/storage/demos` | Owner session or API token. | None. | Demo storage report from `demo_storage_report()`. Exact nested schema is service-owned. | `read` |
| `POST` | `/api/storage/demos/manifest` | Owner session plus CSRF, or API token. | None. | Writes manifest and returns `{"ok": true, "manifest_path": ..., "totals": ...}`. | `artifact-write` |
