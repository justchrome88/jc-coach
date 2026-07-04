# WP-014A Steam/Valve One-Button Import Diagnosis

## RESULT

DIAGNOSED

## Primary Import Definition

The `v0.6` primary import is the logged-in owner's one-button Steam/Valve flow from the account/import settings page:

1. Validate that a Steam account is connected.
2. Validate that a Game Authentication Code and latest match share-code cursor exist.
3. Create an `import_job` before any Steam, download or parser work begins.
4. Fetch new Valve/Steam match sharing codes or match references.
5. Skip already-known matches deterministically.
6. Download demos only for new or missing matches.
7. Parse demos with the current parser.
8. Persist parsed match data.
9. Delete raw demo files only after successful parse and DB persistence.
10. Record cleanup status and report clear success, no-new, duplicate, partial and error states.

Manual demo upload is secondary. It remains useful as a parser fixture/debug path, but it is not the main `v0.6` user import.

## Current UI/Button Flow

- Page: `GET /settings/imports`, rendered by `app/templates/import_settings.html`.
- Primary visible controls:
  - "Обновить и скачать демки" posts to `POST /settings/imports/pull-all`.
  - Header/row controls also post to `POST /settings/imports/pull-all`.
  - "Сохранить коды" posts to `POST /settings/imports/steam/{id}/auth-code`.
  - Queued/failed `match_history_sync` rows can be run through `POST /settings/imports/jobs/{job_id}/run`.
- Route: `pull_all_steam_imports()` calls `queue_steam_import_all()`.
- Background behavior: if the job is queued, the route adds FastAPI `BackgroundTasks` to run `_run_steam_import_all_background(job.id)`, which opens its own `SessionLocal()` and calls `run_steam_import_all_job()`.
- DB tables touched by the intended primary path: `import_jobs`, `steam_accounts`, `matches`, parser-derived match evidence/artifact tables, recommendations/evaluations touched by parser side effects, and app settings for key/code setup routes.
- Exact share-code demo import route `POST /settings/imports/steam/{id}/share-code` calls `import_steam_share_code_demo()` directly and does not create an `import_job`; this violates the non-negotiable rule for any import process that starts download/parser work.

## Current Backend Flow

- Steam account connection:
  - `steam_accounts` stores `user_id`, `steam_id`, `persona_name`, `linked_at`, `last_sync_at`, `sync_enabled`, `match_auth_code` and `last_share_code`.
  - Steam OpenID callback requires the current owner session before linking.
- Match/auth code:
  - `update_match_auth_code()` stores `match_auth_code` and optional latest share-code cursor, enables sync and queues a `match_history_sync` job.
- Cursor/start point:
  - `steam_accounts.last_share_code` is the saved cursor.
  - `import_jobs.requested_payload_json.known_share_code` may override the cursor for a single `match_history_sync`.
  - `knowncode=0` is only an initial sentinel when no saved cursor exists.
- Share-code fetch:
  - `sync_match_history_job()` calls Valve `GetNextMatchSharingCode` through `app.services.steam_integration`.
  - It stores collected share codes as `matches(source="steam_history", external_match_id=<share_code>)`.
  - Duplicate share codes are detected by the source/external id uniqueness surface.
  - Cursor advance occurs after local share-code persistence.
- Primary pull-all:
  - `run_steam_import_all_job()` marks `steam_import_all` as running, iterates accounts, stores the saved cursor share code, queues/runs `match_history_sync`, marks fresh share codes as demo-download pending, then calls `download_pending_steam_demos()`.
  - Missing auth code or cursor is currently recorded as a skipped account inside a job that can still finish `succeeded`; it is not surfaced as a first-class `need_code` state.
- Demo download:
  - `download_pending_steam_demos()` selects `steam_history` matches with no `demo_file` and status not `demo_download_error`.
  - A Node Steam GC helper resolves demo URLs and metadata.
  - `_download_demo_file()` downloads `.dem.bz2` or `.dem` to a temporary directory and decompresses `.bz2`.
- Parser/persistence:
  - `_download_and_import_match()` calls `import_demo_file()` with Steam GC metadata.
  - `import_demo_file()` copies the demo into `data/uploads`, parses it, persists/updates a `matches(source="demo")` row and parser artifacts, and can trigger recommendation evaluation side effects.
  - After import, the `steam_history` placeholder raw JSON is updated to `demo_imported` with `steam_metadata`, `played_at`, `played_at_source`, `imported_demo_match_id` and `imported_at`.
- Error/no-new/duplicate behavior:
  - `match_history_sync` has tested outcomes for new, no-new, duplicate-only and temporary Steam errors.
  - `steam_import_all` always marks the aggregate job `succeeded` unless an exception escapes, even when individual accounts are skipped or demo downloads fail.
  - Demo URL/download/parser failures are collapsed into `demo_download_error`.

## Current DB State

Read-only query against `data/cs2_coach.db` on 2026-07-04:

- DB SHA before and after read-only inspection: `be2a54fef35227129ae2023931e76d2cf20e100ae09d9ec7e7477f1755526fc2`.
- `steam_accounts`: 1.
- `import_jobs`: 12.
- `matches`: 59.
- `import_jobs` by status:
  - `succeeded`: 8.
  - `failed`: 2.
  - `queued`: 2.
- `import_jobs` by type/status:
  - `match_history_sync`: 4 succeeded, 1 failed, 1 queued.
  - `steam_import_all`: 4 succeeded, 1 failed.
  - `steam_openid_linked`: 1 queued.
- Steam account summary:
  - one linked Steam account for `users.id=1`;
  - `sync_enabled=1`;
  - match auth code present;
  - last share-code cursor present;
  - latest `last_sync_at`: `2026-07-02 22:44:42.139926`.
- `steam_history` match statuses:
  - `ignored_old_history`: 40.
  - `demo_download_pending`: 1.
- Latest successful `steam_import_all` jobs processed share-code batches but imported zero demos because GC `match_time` was not newer than the latest imported match. Older job `id=6` recorded 16 imported and 4 failed demo downloads.

## queued/running import_jobs classification

No running import jobs were found.

Stale queued jobs:

- `import_jobs.id=1`, `job_type=steam_openid_linked`, queued since `2026-07-01 12:51:51`: stale/unknown; not part of visible Steam import job list, but stale operational data.
- `import_jobs.id=10`, `job_type=match_history_sync`, queued since `2026-07-02 22:42:41`: stale; it can be manually processed by the current UI.

No queued `steam_import_all` job currently blocks the one-button button. A future stale queued/running `steam_import_all` would block/idempotently reuse the same job because `current_steam_import_all_job()` treats queued/running jobs as current.

## Date/Cursor Problem Analysis

- Share-code cursor:
  - `steam_accounts.last_share_code` is the cursor source of truth.
  - Cursor advancement is based on share-code collection, not demo parse success.
  - Duplicate-only sync may advance cursor to avoid repeated processing.
- Date used for freshness:
  - `run_steam_import_all_job()` computes `latest_imported_match_played_at` from latest non-`steam_history` `Match.played_at`.
  - `download_pending_steam_demos()` skips candidates when Steam GC `match_time` is absent or not newer than that latest imported date.
- Actual match date:
  - Best current source is Steam GC `match_time`, normalized by `steam_gc_metadata_from_item()` and applied as authoritative `played_at`.
  - `steam_history` placeholder rows do not know exact match date until GC metadata is resolved.
  - Manual demo parser date can come from demo header. If unavailable, it falls back to file modified time; this is not an exact match date.
- Current exact-date availability:
  - Exact match date is available only when Steam GC metadata provides a valid `match_time`.
  - If GC metadata is missing, current code can fall back to parser/demo header or file mtime depending on path. The UI/status does not consistently expose exact/unavailable/approximate date truth.
- Risks:
  - Old or wrong `latest_imported_match_played_at` can skip valid historical demos.
  - Manual imports with file-mtime fallback can poison freshness comparisons.
  - Placeholder `created_at`, job time, download time, parsed time or file mtime can be mistaken for match date unless UI/status labels the source.
  - Missing GC `match_time` is currently skipped as old when a latest imported date exists, which can create false no-new/skip behavior.

## Demo Lifecycle Analysis

- Download location:
  - Steam downloads use a temporary `jc-steam-demo-*` directory.
  - `.dem.bz2` is decompressed to `.dem`; the archive is removed from temp storage after decompression.
- Persisted raw demo location:
  - `import_demo_file()` copies the `.dem` into `data/uploads`.
- Cleanup after success:
  - The temporary download directory is removed in `finally`.
  - The persisted raw `.dem` copy in `data/uploads` is not deleted after successful parse/persist.
  - There is no durable cleanup status field for raw demo lifecycle.
- Parser failure:
  - `_download_and_import_match()` converts `DemoParseError` to `SteamDemoDownloadError`.
  - The `steam_history` placeholder is marked `demo_download_error`.
  - Because `import_demo_file()` stores a copy before parsing, parser failure can leave a raw copied demo in `data/uploads` with no quarantine/cleanup policy.
- Size risk:
  - Demos are large, about 350 MB. Persisted raw retention without verified cleanup can grow disk usage quickly.
- Current policy gap:
  - `docs/DEMO_STORAGE_TZ.md` already describes a future delete-after-verify lifecycle, but code still follows a retain-raw alpha policy.

## Manual Demo Import Role

Manual upload/import is a secondary debug and fixture acceptance path:

- `GET /upload` and `POST /upload` accept CSV/JSON/DEM.
- `POST /upload/server-demo` imports files from the server inbox.
- Manual DEM import helps parser development and fixture acceptance.
- It must not be treated as the `v0.6` primary user import, and its date source must be labeled honestly when exact match time is unavailable.

## P0 blockers

- Successful Steam demo parse/persist does not delete the persisted raw `.dem` from `data/uploads`; cleanup status is not recorded.
- Parser failure can leave a copied raw `.dem` in `data/uploads` and is only recorded as `demo_download_error`; there is no failed/quarantine/cleanup-needed state.
- Exact share-code demo import can start download/parser work without an `import_job`.
- Aggregate `steam_import_all` can finish `succeeded` while accounts are skipped or demo downloads fail; required states such as `need_code`, `steam_not_connected`, `partial_success`, `download_failed`, `parser_failed` and `rate_limited` are not first-class.
- Exact match date truth is not consistently surfaced; placeholders and manual parser fallbacks can leave UI/status ambiguity.

## P1 risks

- Stale queued `match_history_sync` job exists and can confuse operator workflow.
- `steam_openid_linked` queued job is stale historical data outside the visible import-job workflow.
- Freshness skip depends on latest non-`steam_history` `played_at`, so bad manual dates can cause missed imports.
- Cursor advancement is independent from demo parse/persist success; this may be acceptable but must remain visible in job results.
- No durable retry/backoff ledger exists for Steam/Valve failures.
- Rate limits are currently stored as generic failure/error strings, not a first-class outcome.

## Minimal Repair Plan for WP-014B

1. Make the primary one-button path the only accepted `v0.6` import path and keep `import_job` creation before any external/download/parser work.
2. Add an `import_job` wrapper for exact share-code demo import or explicitly demote/disable that path for production use.
3. Introduce explicit status taxonomy in job/result JSON: `success`, `no_new`, `need_code`, `steam_not_connected`, `rate_limited`, `download_failed`, `parser_failed`, `partial_success`, `duplicate_skipped`, `exact_match_date_available`, `exact_match_date_unavailable`.
4. Separate share-code sync outcome from demo download/parser outcome in `steam_import_all` result and mark aggregate jobs `failed` or `partial_success` when required.
5. Add verified raw demo lifecycle: temp cleanup, persisted raw cleanup after successful parse and DB commit, failed/quarantine/cleanup-policy-needed for failed demos, and cleanup status in result metadata.
6. Treat Steam GC `match_time` as exact; mark missing date as unavailable rather than substituting job/download/created/file-mtime dates in the primary Steam flow.
7. Add stale job diagnosis/recovery policy for queued/running import jobs without mutating them in diagnosis mode.
8. Add mocked regression tests for no-new, duplicate, missing code, disconnected Steam, rate limit, download failure, parser failure, exact date available/unavailable and cleanup behavior.

## Acceptance Criteria for v0.6

Primary path:

- Logged-in owner can open `/settings/imports` and run one-button Steam/Valve import.
- An `import_job` exists before external Steam, download or parser work.
- Connected Steam account and match/auth code are validated.
- New share codes/match references are fetched without duplicating matches.
- Duplicate matches are skipped with a visible duplicate state.
- No-new scenario is reported clearly.
- Download, parser, rate-limit and partial-success states are reported clearly.
- Exact match date is stored from Steam GC metadata or explicitly marked unavailable.
- Job, cursor and match dates are not presented as match dates.
- Downloaded demos are stored predictably.
- Raw demos are deleted only after successful parse and DB persistence.
- Failed demos are marked failed/quarantine/cleanup-policy-needed.
- Parser result is visible in imported matches with Metric Truth labels for weak/unavailable data.

Secondary path:

- Manual demo upload/import remains available for parser fixture/debug acceptance.
- Manual import date truth is labeled and does not silently drive primary Steam freshness decisions when approximate.

## Can Proceed To Repair

yes
