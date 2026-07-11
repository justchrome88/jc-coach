# MVP-002 Import and Demo Storage Safety Contract

Date: 2026-07-09

Task: `MVP-002_IMPORT_AND_DEMO_STORAGE_SAFETY_CONTRACT`

Verdict: `PASS_WITH_WARNINGS`

## Scope And Safety

This was report-only executor diagnostic work. It did not change product code,
database schema, package files, service/deploy configuration, raw demos, parser
artifacts or production data.

Forbidden actions detected: `false`.

Explicitly not run:

- live Steam/Valve API or Game Coordinator calls;
- demo download, decompression or parser jobs;
- evaluator or manual evaluator jobs;
- production DB mutation, schema migration or stale-job repair;
- raw demo delete, move or compression;
- service restart or runtime/deploy change;
- `git add`, commit or push.

The generated context manifest was used. Broad Cold reads were avoided. The
stdin MVP-003/MVP-004/MVP-005 task-card names were treated as future queue
context only and were not executed.

## Files Read

Hot/source-of-truth:

- `AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/project_management/WP_REGISTRY.md`
- `/opt/jc-coach-pm/indexes/current_context_manifest.json`
- `/opt/jc-coach-pm/task_cards/mvp_queue_compact_v1/2026-07-09_MVP-002_IMPORT_AND_DEMO_STORAGE_SAFETY_CONTRACT_task-card.md`
- `/opt/jc-coach-pm/docs/task_card_profiles/MVP_TASK_CARD_SAFETY_PROFILES.md`

Task-relevant docs/code/tests:

- `docs/STEAM_IMPORT.md`
- `docs/STEAM_IMPORT_ARCHITECTURE.md`
- `docs/SECURITY.md`
- `docs/TESTING.md`
- `app/config.py`
- `app/db/models.py`
- `app/web/routes.py`
- `app/api/routes.py`
- `app/services/steam_integration.py`
- `app/services/steam_demo_downloader.py`
- `app/services/steam_storage_guard.py`
- `app/services/demo_parser.py`
- `app/services/demo_storage.py`
- `app/services/demo_retention.py`
- `app/templates/import_settings.html`
- `app/templates/storage_settings.html`
- `tests/test_steam_integration.py`
- `tests/test_steam_cursor_truth.py`
- `tests/test_steam_storage_guard.py`
- `tests/test_demo_storage.py`
- `tests/test_importer.py`
- `tests/test_db_import_order.py`

Historical `docs/audit/**` reports were not opened because the manifest marked
them forbidden by default and the current task did not require them.

## Current Import Lifecycle

Primary owner UI path:

1. `/settings/imports` shows Steam account state, current import job, pending
   demo counters and downloader readiness.
2. `/auth/steam/callback` requires an owner session before linking Steam and
   creates only a metadata `steam_openid_linked` job.
3. `/settings/imports/steam/{id}/auth-code` stores the Game Authentication Code
   plus latest share-code cursor, stores the cursor as a `steam_history` match
   row and creates a queued `match_history_sync` job.
4. `/settings/imports/pull-all` calls `queue_steam_import_all()`. That marks
   stale running parent jobs interrupted, reuses any active queued/running
   parent, or creates a new `steam_import_all` parent job.
5. If the parent is newly queued, FastAPI `BackgroundTasks` runs
   `_run_steam_import_all_background()`, which opens its own DB session and
   calls `run_steam_import_all_job()`.
6. `run_steam_import_all_job()` performs storage preflight, checkpoints
   progress into `ImportJob.result_json`, validates account readiness, queues
   and runs child `match_history_sync` jobs, marks fresh share codes as demo
   pending, then calls `download_pending_steam_demos()`.
7. `download_pending_steam_demos()` resolves demo URLs through the Steam GC
   helper, downloads/decompresses to a temporary directory, imports via
   `import_demo_file(..., evaluate_recommendations=False)`, applies Steam GC
   date truth and records raw demo retention metadata.

Secondary/manual paths:

- `/settings/imports/steam/{id}/share-code` calls
  `import_steam_share_code_demo()` and remains a non-primary debug/manual path.
- `/settings/imports/jobs/{job_id}/run` and `/settings/imports/run-queued`
  run queued `match_history_sync` jobs.
- API paths under `/api/steam/import/*` expose equivalent job creation/run and
  overview behavior.
- `/upload` and `/upload/server-demo` can import local/manual demos through the
  parser, but manual upload is secondary and not the target Steam import path.

## Job Status, Cap, Retry And Error Findings

- `ImportJob.status` remains coarse: `queued`, `running`, `succeeded`,
  `failed`. Canonical import truth is in `result_json.overall_outcome`,
  `result_json.statuses`, progress, and error fields.
- `STEAM_IMPORT_MAX_DEMOS_PER_RUN` defaults to `1` in `app/config.py`.
  `SteamImportStorageBudget` also clamps max demos to at least one, and
  `download_pending_steam_demos()` applies the lower effective per-run cap.
- Larger batches remain blocked by Hot docs and the task card. This report does
  not authorize a cap raise.
- Parent `steam_import_all` has checkpointed progress and stale interruption
  handling. Startup stale repair exists but is disabled by default through
  `STEAM_IMPORT_REPAIR_STALE_ON_STARTUP=false`.
- There is no durable worker, lease/heartbeat table or durable retry ledger.
  Current retry is operator-driven through queued job routes and explicit stale
  repair procedures.
- Retryability is partially represented by taxonomy/docs, but current runtime
  payloads do not yet consistently include the full target
  `schema_version/source/context/attempt/evidence/safety/retryable` contract.
- `sync_match_history_job()` advances the Steam cursor only after the Steam API
  call and local share-code persistence succeed. On exceptions it fails the job
  and does not advance the cursor.
- `download_failed`, `parser_failed`, `rate_limited`, `disk_budget_exceeded`,
  `demo_too_large`, `storage_preflight_failed`, `batch_cap_reached`,
  `interrupted`, `need_code`, `steam_not_connected`, `no_new`,
  `duplicate_skipped`, exact-date and approximate-date statuses are documented
  and surfaced through result taxonomy.

Warning: the BackgroundTasks runner is acceptable only for current personal
one-demo capped operation. It is not enough for cap raise, larger batch import,
automatic retry or public/friends readiness.

## Demo Acquisition And Storage Lifecycle

Current acquisition flow:

- `steam_demo_downloader_configured()` requires service bot credentials or a
  refresh token.
- `_fetch_demo_urls()` calls the Node Steam GC helper with bot credentials in
  environment variables and stores helper credentials under
  `data/steam_bot_credentials` with `0700` directory permissions.
- `_download_demo_file()` creates an OS temp directory via `tempfile.mkdtemp`,
  streams the archive, enforces byte guards while downloading/decompressing and
  deletes the temporary archive after decompression.
- `import_demo_file()` copies the `.dem` into `UPLOAD_DIR`, parses it, writes
  normalized match/parser rows and returns retention metadata.
- The temporary download directory is removed after parser/import completion or
  download failure. This is temp cleanup, not production raw-demo lifecycle
  cleanup.

Storage guardrails currently implemented:

- preflight on upload and temp directories;
- minimum free-space check;
- preserve-free floor;
- per-job byte budget;
- per-demo byte guard;
- unknown-size reserve;
- streamed download byte counting;
- decompression byte counting;
- upload copy byte counting;
- storage snapshot in progress/result evidence.

Important tempdir finding:

- `SteamImportStorageBudget.temp_dir` uses `tempfile.gettempdir()`. Hot docs
  require shell service calls that touch Steam/import temp storage to set
  `TMPDIR`, `TEMP` and `TMP` to `/opt/jc-coach/data/tmp` when explicitly
  authorized. Future import execution WPs must preserve that requirement in
  command evidence.

## Raw Demo Retention Policy Findings

- Current retention policy is hard-coded as
  `retain_raw_for_parser_development`.
- `delete_after_success_enabled()` returns `False`.
- Successful parser imports record `retained_for_parser_dev`.
- Parser failures record `retained_after_failure` or `cleanup_needed`.
- `demo_storage_report()` is read/report oriented: it classifies referenced,
  missing, unreferenced, suspicious and future deletion-candidate files; it does
  not delete raw demos.
- `/settings/storage/manifest` writes a JSON manifest report. That is a
  persistent app report/data artifact and must not be run in future report-only
  tasks unless explicitly authorized.
- `delete_raw_demo_after_success()` contains the future deletion primitive, but
  default `enabled=False` prevents deletion.
- `demo_parser.import_demo_file()` deletes a newly copied duplicate demo file
  when an existing imported match already has a different `demo_file`. That is
  duplicate-copy cleanup, not accepted general raw-demo cleanup; future storage
  WPs must explicitly review whether this behavior remains allowed.
- `_download_demo_file()` deletes temporary archives and temp directories during
  failure/success cleanup. This should remain scoped to temp files only.

Warning: no raw demo delete/move/compress policy is accepted for production
retained demos. Future delete-after-success requires a separate storage WP with
backup/manifest/evidence and explicit raw-demo lifecycle authorization.

## Idempotency And Duplicate Protection Findings

Implemented protections:

- `matches` has a unique constraint on `(source, external_match_id)`.
- `_store_steam_share_code_match()` catches `IntegrityError` and treats an
  existing share code as duplicate.
- `queue_steam_import_all()` is single-flight at parent-job level for active
  queued/running `steam_import_all` rows.
- `mark_stale_steam_import_all_jobs_interrupted()` prevents indefinite reuse of
  stale running parent jobs.
- `sync_match_history_job()` records inserted/duplicate counts and cursor
  decisions in `result_json`.
- `import_demo_file()` deduplicates parsed demo matches by `source` and
  `external_match_id`, updates existing parser payload/artifacts, and returns a
  duplicate result rather than creating a second match row.
- Demo parse artifacts have a unique `match_id` constraint.

Gaps before cap raise or automated retry:

- No durable idempotency key is persisted for a logical import unit.
- No durable attempt ledger exists.
- Parent and child jobs are linked only through JSON progress/result payloads,
  not a normalized relation.
- Targeted pending-demo imports can run without a parent `steam_import_all`
  metadata surface.
- There is no accepted raw-demo checksum ledger for retained files. Parser
  artifacts store `demo_sha1`, and the storage report computes only a short
  SHA-256 for suspicious small files.
- Single-flight is process/DB-row oriented for the parent job and does not
  fully lock share-code, demo URL, raw path or checksum work units.

## Safety Gates Before Live Import

Any future live Steam/Valve import task must include all of the following:

- explicit authorization to run the named import path;
- branch and clean worktree evidence;
- declaration that `STEAM_IMPORT_MAX_DEMOS_PER_RUN` remains `1`, unless the WP
  is an explicit cap-change task;
- explicit production DB authorization status, with backup and pre/post SHA if
  mutation is allowed;
- exact command/route path and whether it is browser/UI, API, script or shell;
- `TMPDIR=/opt/jc-coach/data/tmp`,
  `TEMP=/opt/jc-coach/data/tmp` and `TMP=/opt/jc-coach/data/tmp` for shell
  service calls touching Steam/import temp storage;
- storage preflight and post-run storage evidence;
- import job IDs and terminal `ImportJob.status`;
- `result_json.overall_outcome`, `statuses`, clean-success flag and
  retryability/error evidence;
- whether Steam cursors advanced;
- whether demo download, decompression or parser ran;
- retained raw-demo paths and byte counts, without deleting/moving/compressing
  retained raw demos;
- explicit statement that evaluator/manual evaluator did or did not run;
- no public/friends readiness claim.

Stop before execution if any required evidence would require a broader task,
service change, DB/schema mutation, raw-demo lifecycle action, package change
or cap raise not named by the task card.

## Safety Gates Before Raw-Demo Lifecycle Changes

Before deleting, moving, compressing or rewriting retained raw demos, a future
storage WP must require:

- explicit raw-demo lifecycle authorization and allowed paths;
- pre-action manifest from a task-authorized storage report;
- production DB backup/SHA if any DB references or retention metadata mutate;
- file inventory with DB reference status, size and content identity;
- policy for referenced, unreferenced, missing, suspicious, duplicate and
  parser-failed demos;
- proof parsed payloads/artifacts are sufficient for accepted metrics;
- rollback/restore note and backup/storage location;
- post-action manifest and disk usage evidence;
- no parser/evaluator/import rerun unless separately authorized.

## Recommended WP-020..WP-035 Sequence

1. `WP-020_IMPORT_RESULT_JSON_CONTRACT_ACCEPTANCE`: accept the target JSON
   contract for terminal and in-progress import outcomes without schema
   mutation.
2. `WP-021_IMPORT_JOB_STATUS_AND_RETRY_LEDGER_PLAN`: design durable attempts,
   retryability, backoff and idempotency keys.
3. `WP-022_IMPORT_WORKER_SINGLE_FLIGHT_PLAN`: define durable worker, lease,
   stale, cancellation and resume behavior.
4. `WP-023_IMPORT_UI_API_SAFETY_SURFACE`: ensure UI/API expose outcome,
   progress, cap, retained files and retry state without overclaiming.
5. `WP-024_LIVE_IMPORT_ONE_DEMO_EXECUTION`: explicitly authorized one-demo
   capped live import with DB backup/SHA and tempdir evidence.
6. `WP-025_IMPORT_RETRY_AND_STALE_REPAIR_ACCEPTANCE`: accept operator-driven
   retry/stale repair rules before automation.
7. `WP-026_IMPORT_CAP_CHANGE_GATE`: only after worker/retry/result acceptance,
   decide whether any cap raise is allowed.
8. `WP-030_DEMO_STORAGE_INVENTORY_CONTRACT`: accept manifest fields and file
   identity policy.
9. `WP-031_RAW_DEMO_RETENTION_POLICY`: choose retained raw lifecycle states
   and owner/operator responsibilities.
10. `WP-032_DEMO_CHECKSUM_AND_REFERENCE_LEDGER_PLAN`: design checksum/path/DB
    reference tracking before cleanup.
11. `WP-033_DELETE_AFTER_SUCCESS_READINESS_REVIEW`: verify parser artifacts and
    metrics are sufficient before any deletion mode.
12. `WP-034_RAW_DEMO_CLEANUP_DRY_RUN`: dry-run only, no delete/move/compress.
13. `WP-035_RAW_DEMO_LIFECYCLE_EXECUTION`: execute only if explicitly
    authorized with backup, manifest and rollback evidence.

## Required Next Task

Recommended next task:
`MVP-003_DB_SCHEMA_DATA_STORAGE_MUTATION_PLAN`.

That task should remain report/plan oriented until it explicitly receives
production DB/schema/data mutation authority with backup and pre/post SHA
requirements.

## Checks Run

- `git status --short` before work: clean.
- `git branch --show-current`: `cona`.
- `.venv/bin/python scripts/project_gate.py preflight`: PASS; production DB
  SHA read-only evidence:
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
- `git diff --check`: PASS.
- `.venv/bin/python scripts/project_gate.py changed`: PASS; changed file is
  only this untracked allowed report.
- `.venv/bin/python scripts/project_gate.py required-checks`: PASS; activated
  guardians were `DOCUMENTATION_STEWARD`, `IMPORT_GUARDIAN` and
  `PM_ORCHESTRATOR`.
- `.venv/bin/python scripts/project_gate.py postflight`: PASS; production DB
  SHA read-only evidence remained
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
- `git status --short` after work: only
  `?? docs/audit/MVP_002_IMPORT_AND_DEMO_STORAGE_SAFETY_CONTRACT.md`.

Guardian confirmations:

- Hot/current status docs update: not required; this task writes a standalone
  executor report only.
- Navigation docs update: not required; report path is task-card specified.
- Live Steam/import/parser jobs run: no.
- Steam cursor mutation: no.
- Production DB mutation: no; production DB SHA was read only by project gate.
- Unauthorized `git add`/commit/push: no.

Full tests, Ruff, local quality gate and recommended mocked import/parser test
sets were not run because this was a docs-only report task, no code/tests were
changed and the task card said not to run full tests or import/parser/evaluator
commands.

## Residual Risks

- Contract acceptance does not itself implement durable retry, durable worker
  leases, raw-demo checksum ledger or delete-after-success readiness.
- Existing code still contains live import/parser/data mutation routes; they
  remain forbidden unless a future task explicitly authorizes execution.
- Storage report manifest generation is a persistent artifact write and should
  be treated as separately authorized storage/report work.
- Current personal import acceptance remains one-demo capped with warnings and
  does not imply public/friends readiness.
