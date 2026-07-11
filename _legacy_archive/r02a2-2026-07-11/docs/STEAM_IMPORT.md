# Steam Import

Last updated: 2026-07-08.

Canonical supporting docs:

- `docs/STEAM_IMPORT_ARCHITECTURE.md`
- `docs/STEAM_MATCH_DATES_RU.md`

## Accepted Flow

1. User signs in with Steam OpenID.
2. User provides Game Authentication Code and latest `CSGO-...` share-code cursor from Steam Support.
3. Server operator configures `STEAM_WEB_API_KEY`.
4. Dedicated service bot resolves known share codes through the CS2 Game Coordinator.
5. App downloads `.dem.bz2`, decompresses to `.dem`, imports through parser and stores Steam GC `match_time` as authoritative `played_at`.

## Primary v0.6 Target

The primary `v0.6` import is one-button Steam/Valve import from the logged-in owner's import/settings page. Manual demo upload is secondary and exists for parser fixtures/debugging.

Required primary behavior:

- the user opens `/settings/imports` and clicks "Обновить и скачать демки";
- the app validates a connected Steam account;
- the app validates the Game Authentication Code and latest share-code cursor;
- an `import_job` exists before any Steam, demo download or parser work begins;
- new share codes or match references are fetched from Valve/Steam;
- duplicates are skipped without creating duplicate match records;
- demos are downloaded only for new or missing matches;
- demos are parsed with current parser capabilities and weak/unavailable facts stay governed by Metric Truth;
- parsed data and match records are persisted before any future cleanup;
- current policy retains raw demo files for parser development by default;
- future delete-after-success mode may delete raw demos only after successful parse and DB persistence, but it is disabled now;
- failed demos are classified as failed/quarantine/cleanup-policy-needed;
- statuses distinguish success, no-new, need-code, Steam-not-connected, rate-limited, download-failed, parser-failed, partial-success, duplicate-skipped and exact match-date available/unavailable.

Exact match date means the actual match datetime from Valve/Steam/demo metadata. Job creation time, download time, parser time, DB creation time and file mtime must not be presented as match date.

## Current Status

Steam import is accepted for controlled personal `v0.6` with warnings. It is not friends/public ready.

WP-014A diagnosis found that the current one-button UI and backend path exist, but `v0.6` acceptance is blocked by incomplete status taxonomy, incomplete `import_job` coverage for exact share-code download/parser work, missing persisted raw-demo cleanup after successful parse/persist, weak failed-demo cleanup policy and inconsistent exact-date availability surfacing. See `docs/audit/WP_014A_STEAM_VALVE_IMPORT_DIAGNOSIS.md`.

WP-014B1 repaired import-job truth/status taxonomy without changing schema or demo cleanup lifecycle. The primary `steam_import_all` job now records `overall_outcome`, `statuses`, `clean_success`, `error_message` and the existing-status limitation in `result_json`. Exact share-code import is tracked by a `share_code_import` job before downloader/parser work, but remains a non-primary debug/manual path.

Standardized result statuses:

- `success`;
- `no_new`;
- `need_code`;
- `steam_not_connected`;
- `rate_limited`;
- `download_failed`;
- `parser_failed`;
- `partial_success`;
- `duplicate_skipped`;
- `exact_match_date_available`;
- `exact_match_date_unavailable`;
- `approximate_match_date`.
- `disk_budget_exceeded`;
- `batch_cap_reached`;
- `demo_too_large`;
- `storage_preflight_failed`.
- `interrupted`.

`ImportJob.status` still has only `queued`, `running`, `succeeded` and `failed`. Clean `success`, `no_new` and `duplicate_skipped` outcomes may use `succeeded`. Partial success is represented in `result_json.overall_outcome/statuses` and persisted as `failed` to avoid clean-success overclaim until a future schema/status migration is explicitly approved.

Import cap status: `STEAM_IMPORT_MAX_DEMOS_PER_RUN` remains `1`. Larger Steam
demo batches remain blocked until the import outcome taxonomy, `result_json`
schema, durable worker plan and retry ledger plan are accepted by the
foundation-hardening review, and until a separate explicit cap-change WP
authorizes the cap change. This contract does not approve a cap raise.
Warning-ledger carry-in `WL-FH-000-028` remains preserved for this blocker
until PM review accepts the worker/retry/result safety contract or creates a
successor warning.

WP-014B2 repaired exact match-date truth without changing schema or demo cleanup lifecycle. For the primary Steam/Valve path, `Match.played_at` is exact only when Steam GC metadata provides valid `match_time` with source `steam_gc_match_time`. If Steam GC `match_time` is missing, primary Steam import records `exact_match_date_unavailable`, clears the imported match `played_at` instead of retaining parser/file-mtime fallback as a match date, and records date truth in `raw_json`/`result_json`. Steam freshness comparison now uses only exact imported Steam dates; manual/file-mtime fallback dates do not silently block new Steam imports.

WP-014B3 made demo retention explicit without enabling deletion. Current policy is `retain_raw_for_parser_development`; successful imports record `retained_for_parser_dev`, parser failures record `retained_after_failure` or `cleanup_needed`, and result/raw JSON include raw demo path/size when available. `delete_after_success` remains disabled by default and is future production mode after parser acceptance.

WP-014C live one-button acceptance failed. One authorized click on `/settings/imports` -> `POST /settings/imports/pull-all` created parent job `#15` and child `match_history_sync` job `#16`. The child sync succeeded, but the parent remained `running` with null `result_json` while multiple large raw demos were retained. `data/uploads` grew from `68K` to `3.1G`, root free space fell to `508M`, graceful service restart hung waiting for background tasks, and a force kill was required to protect the host. No production demo files were deleted and no schema changes were made.

WP-014D1 repaired the storage/batch part of that failure without live Steam work, production DB mutation or file cleanup. One-button demo download now has configurable disk preflight, per-run demo cap, per-job byte budget, per-demo byte guard, preserve-free checks before download/decompression/upload copy, streamed download with byte counting, and first-class result statuses for `disk_budget_exceeded`, `batch_cap_reached`, `demo_too_large` and `storage_preflight_failed`.

WP-014D2 repaired parent progress and stale/interrupted job handling without live Steam work, production DB mutation or production file cleanup. Parent `steam_import_all` jobs now commit bounded `result_json.progress` checkpoints after major phases (`started`, account checks, share-code fetch, demo queue/download/decompress/store, parser success/failure, disk budget and batch cap). Queueing a new one-button import now marks stale running parent jobs as failed/interrupted before creating a new job; non-stale running jobs remain blocking. Best-effort background-task interruption marking exists for soft in-process interruption. Startup stale repair is implemented but disabled by default through `STEAM_IMPORT_REPAIR_STALE_ON_STARTUP=false`.

Operator repair for WP-014C job `#15` is intentionally explicit. Before repair, back up `data/cs2_coach.db`, record the DB SHA, then run:

```bash
python3 scripts/repair_stale_steam_import_job.py --job-id 15 --i-have-backup --confirm-interrupt
```

WP-014D3 executed that explicit operator repair for production job `#15` with backup/SHA evidence. Job `#15` is now `failed` with `overall_outcome: interrupted` and `statuses: ["interrupted"]`; backup is `data/manual_backups/cs2_coach_before_wp014d3_repair_job15_20260704_183815.db`. Only job `#15` changed logically. No live Steam/import/parser work ran, no production demo files were deleted or moved, and `data/uploads` remained `3.1G`.

WP-014C3 repeat one-button live acceptance after the TMPDIR fix proved the storage guard path but still failed acceptance. Service temp resolved to `data/tmp`, storage preflight passed, one authorized click downloaded/stored exactly one raw demo under `STEAM_IMPORT_MAX_DEMOS_PER_RUN=1`, parent job `#18` reached terminal failed state with bounded checkpoints, and disk growth stayed within budget. The failure was a parser/import model mismatch after raw demo retention: Steam date-source metadata added `played_at_source` to the parsed match payload, and `import_demo_file()` passed that non-column key to `Match(...)`.

WP-014E repaired that parser/import model compatibility issue without schema change. Date-source truth (`played_at_source`, `match_date_status`, `match_date_source`) remains represented in `matches.raw_json` and Steam result payloads; only real `matches` table columns are passed to the SQLAlchemy `Match` constructor.

WP-014C4 repeat one-button live acceptance after parser repair passed with warnings and promoted controlled personal import acceptance to `v0.6`. One authorized click created parent job `#20`, storage/TMPDIR guard passed, batch cap limited the run to exactly one demo, parser/import succeeded, exact date truth was persisted via `steam_gc_match_time`, parent `result_json` reached terminal truthful `batch_cap_reached` with `success` and `exact_match_date_available`, service stayed healthy, and disk growth was bounded. Carried warnings: `ImportJob.status` remains coarse and may be `failed` for non-clean outcomes like `batch_cap_reached`; canonical truth is `result_json.overall_outcome/statuses`; uploads/temp still live on root; raw demos are retained by policy; parser memory peak should be watched; friends/public readiness remains blocked.

WP-015A/WP-015A1 reconciled historical match-date truth without reset/resync, live Steam/API, parser jobs, schema changes or production file changes. Rows `21-24` were exact-backfilled from linked `steam_history` rows `5-8`; rows `1-8` and `59` were normalized as non-playable placeholder metadata; rows `37-38` remain playable approximate/file-mtime fallback. Metrics must treat only `match_date_status=exact_match_date_available` with `match_date_source=steam_gc_match_time` as exact and must not use `source="steam_history"` placeholders as playable matches.

WP-015C consumes that import/date truth in metric surfaces. Recent/trend/form/report/recommendation/AI date-window metrics now use exact playable rows for exact windows, count approximate rows as excluded, and expose confidence metadata instead of silently treating file-mtime fallback rows as exact evidence.

Stage 1 security hardening verifies Steam OpenID callback assertions through Steam `check_authentication` before linking an account. A callback that only provides a `claimed_id` is rejected.

Stage 2 ownership hardening requires current owner session for `/auth/steam/callback`. Без owner session callback не создаёт uncontrolled user, `steam_accounts` или `import_jobs`. При owner session Steam account линкуется только к owner user.

Stage 7 Steam cursor truth hardening documents and tests deterministic cursor transitions without live Steam calls, production jobs, production DB mutation or schema changes.

## Cursor Source Of Truth

- `steam_accounts.last_share_code` is the saved latest share-code cursor for the owner-linked Steam account.
- `import_jobs.requested_payload_json.known_share_code` may override the saved cursor for that one job only.
- `knowncode=0` is not a normal latest cursor. It is allowed only as `initial_sentinel_no_saved_cursor` when the account has no saved `last_share_code`.
- Steam GC `match_time`, not the share-code string itself, remains the authoritative match date once the service bot resolves metadata.
- Existing `matches(source="steam_history", external_match_id=<share_code>)` rows are the dedupe surface for collected share codes.

## Cursor Advance Rules

- On successful match-history sync with new collected share codes, the app stores/dedupes local `steam_history` rows first and then advances `steam_accounts.last_share_code` to the last collected code.
- On successful sync with no new share codes, the cursor is not changed and the outcome is `SUCCESS_NO_NEW_MATCHES`.
- On duplicate-only sync, no duplicate rows are created; the cursor may advance to the duplicate collected code to avoid reprocessing the same chain. The outcome is `DUPLICATE_ALREADY_IMPORTED`.
- On Steam/API failure or local persistence failure, the job fails and the cursor is not advanced.
- Manual exact share-code import still sets `last_share_code` to the submitted code because that action is an explicit operator mutation.

## Sync Outcome Semantics

`ImportJob.result_json` for match-history sync records:

- `sync_outcome`: `SUCCESS_NEW_MATCH_IMPORTED`, `SUCCESS_NO_NEW_MATCHES`, `DUPLICATE_ALREADY_IMPORTED` or `STEAM_TEMPORARY_ERROR`.
- `cursor_source`: `job_requested_payload`, `steam_account.last_share_code` or `initial_sentinel_no_saved_cursor`.
- `knowncode_zero_is_initial_sentinel`: `true` only for the initial no-cursor case.
- `cursor_advanced`: whether `steam_accounts.last_share_code` changed after successful local persistence.

These names describe Steam share-code collection state, not guaranteed demo parser/import completion. Demo download and parser import remain separate explicit steps.

## Import Job Outcome Contract

This section is the contract-level target for import-related work. It documents
the expected shape and safety rules only. It does not change database schema,
runtime behavior, worker behavior, import cap, live Steam access, parser
execution or production DB state.

`ImportJob.status` is a coarse lifecycle field:

- `queued`: work is waiting for an explicitly authorized runner.
- `running`: a runner has claimed the job and must keep reviewable progress in
  `result_json.progress` when the path supports checkpoints.
- `succeeded`: the job reached a clean terminal outcome such as `success`,
  `no_new` or `duplicate_skipped`.
- `failed`: the job reached a terminal problem, partial-success boundary,
  interruption, cancellation or safety stop.

`result_json` is the canonical outcome field. Operators, PM reviews, UI labels,
tests and future worker logic must read `result_json.overall_outcome`,
`result_json.statuses`, `result_json.retryable` and evidence fields before
claiming success or deciding retry behavior. A coarse `failed` row can still be
an expected safety result, for example `batch_cap_reached` after a bounded
successful one-demo import.

### Outcome Taxonomy

Outcome names are stable report vocabulary. Implementation can add service
specific detail, but it must not collapse retryable, terminal and partial
outcomes into ambiguous strings.

| Outcome/status | Class | Retryability | Required meaning |
|---|---|---|---|
| `success` | terminal clean | no | Requested import work completed without safety caveats beyond documented source limits. |
| `no_new` | terminal clean | no | Steam/share-code sync found no new work and did not mutate demo/match data beyond expected job metadata. |
| `duplicate_skipped` | terminal clean | no | Candidate was already represented and no duplicate match was created. |
| `need_code` | terminal operator action | no automatic retry | Owner/operator must provide or refresh Game Authentication Code or latest share-code cursor. |
| `steam_not_connected` | terminal operator action | no automatic retry | Owner Steam account is absent or not linked for the requested Steam import path. |
| `rate_limited` | transient external | retryable with backoff | Steam/Valve or local throttle rejected the request; cursor must not advance on failed external or local writes. |
| `download_failed` | transient or terminal external/storage | conditional | Demo download failed. Retry only if evidence says URL, network, space and cap state make retry safe. |
| `parser_failed` | terminal until parser/data issue is reviewed | no automatic retry | Downloaded demo could not be parsed or imported. Raw retention and cleanup status must be explicit. |
| `partial_success` | terminal with warnings | no automatic retry without review | Some work persisted and some failed. `ImportJob.status` should remain conservative and `result_json` must identify persisted and failed parts. |
| `exact_match_date_available` | evidence tag | not applicable | Steam GC `match_time` was persisted as exact match date source. |
| `exact_match_date_unavailable` | evidence tag | not applicable | Exact Steam GC match date was missing or invalid; no approximate date may be presented as exact. |
| `approximate_match_date` | evidence tag | not applicable | A non-exact date exists only as caveated fallback evidence. |
| `disk_budget_exceeded` | safety stop | retryable after operator/storage action | Storage guard stopped work before exceeding configured budget. |
| `batch_cap_reached` | safety stop | no automatic retry | Per-run cap stopped the batch as designed. It does not authorize a larger cap. |
| `demo_too_large` | safety stop | no automatic retry without explicit review | A candidate exceeded per-demo size limits. |
| `storage_preflight_failed` | safety stop | retryable after operator/storage action | Preflight found insufficient or unsafe storage/temp state before download/parser work. |
| `interrupted` | safety stop | conditional | Process shutdown, stale repair or operator interruption ended the job. Retry requires stale-state review. |
| `cancelled` | terminal operator action | no automatic retry | Operator intentionally cancelled queued/running work. Future implementation must preserve reviewable evidence. |
| `worker_lost` | safety stop | retryable only after lease/stale review | Durable worker heartbeat or lease expired before terminal outcome. |
| `worker_conflict` | safety stop | no automatic retry until conflict cleared | Single-flight or idempotency guard found another active runner for the same import unit. |
| `invalid_request` | terminal input/config | no automatic retry | Request payload, job type or required context was invalid. |
| `unauthorized` | terminal auth/safety | no automatic retry | Owner/auth/API boundary failed or the task lacked explicit live/import/parser/evaluator authorization. |
| `schema_or_contract_mismatch` | terminal implementation | no automatic retry | Runtime payload did not match current model/schema/contract; requires implementation review. |

### Expected `result_json` Shape

Future import paths should preserve the existing fields and add compatible
structured fields rather than replacing them. Schema-changing persistence is a
separate approval-required scope; this shape is a JSON contract only.

Required top-level fields for terminal import outcomes:

```json
{
  "schema_version": 1,
  "job_type": "steam_import_all",
  "overall_outcome": "batch_cap_reached",
  "statuses": ["success", "batch_cap_reached", "exact_match_date_available"],
  "clean_success": false,
  "retryable": false,
  "error": null,
  "source": {
    "provider": "steam",
    "steam_account_id": 1,
    "share_code": "redacted-or-omitted",
    "cursor_source": "steam_account.last_share_code"
  },
  "context": {
    "cap": 1,
    "tmpdir": "/opt/jc-coach/data/tmp",
    "worker": "background_task",
    "idempotency_key": "job-type/source/candidate"
  },
  "progress": [
    {"phase": "started", "status": "ok"},
    {"phase": "storage_preflight", "status": "ok"}
  ],
  "attempt": {
    "number": 1,
    "max_attempts": 1,
    "next_retry_at": null,
    "backoff_seconds": null
  },
  "evidence": {
    "created_match_ids": [],
    "updated_match_ids": [],
    "retained_demo_paths": [],
    "raw_demo_bytes": 0,
    "match_date_source": "steam_gc_match_time"
  },
  "safety": {
    "cursor_advanced": false,
    "production_db_touched": true,
    "live_steam_calls": true,
    "parser_ran": true,
    "manual_evaluator_ran": false
  }
}
```

Field expectations:

- `schema_version` identifies the JSON contract version, not a DB migration.
- `overall_outcome` is one primary value from the outcome taxonomy.
- `statuses` is a list of outcome/evidence tags. It can include both work
  result and safety/evidence statuses.
- `clean_success` is `true` only when the outcome can be safely summarized as
  complete success without partial/safety caveats.
- `retryable` must be explicit for every terminal problem or safety stop.
- `error` should be `null` for clean outcomes; otherwise it should include
  `code`, `message`, `stage`, `retryable` and a redacted `detail` when useful.
- `source` records provider and safe context. It must not include secrets,
  Steam auth-code values, refresh tokens, passwords or full sensitive payloads.
- `context` records cap, temp-directory, worker mode and idempotency context.
- `progress` records reviewable checkpoints for long-running paths.
- `attempt` is present even before a durable retry ledger exists, with
  operator-driven attempts recorded as best available evidence.
- `evidence` links to persisted rows, retained raw demos, byte counts and date
  truth without exposing secret values.
- `safety` states which high-risk side effects actually happened.

Minimum required fields for non-terminal checkpoints:

```json
{
  "schema_version": 1,
  "job_type": "steam_import_all",
  "overall_outcome": "running",
  "statuses": ["running"],
  "clean_success": false,
  "retryable": null,
  "progress": [{"phase": "download", "status": "running"}],
  "safety": {
    "cursor_advanced": false,
    "live_steam_calls": true,
    "parser_ran": false
  }
}
```

## Durable Worker Contract Plan

A future durable import worker must be designed and accepted before any import
cap raise or larger batch operation. The current `BackgroundTasks` path remains
acceptable only for controlled personal one-demo-capped work.

Contract-level worker requirements:

- Queue/resume: import work must be represented by durable job rows before
  Steam, download, parser or evaluator work begins. A worker restart must be
  able to identify `queued`, `running`, stale, terminal and cancelled jobs.
- Single-flight: at most one runner may process a logical import unit at a
  time. Logical units include job ID, Steam account, share-code candidate,
  retained demo path and idempotency key.
- Idempotency: retries and resumes must not duplicate match rows, parser
  artifacts, raw demo copies, cursor advancement or recommendation/evaluation
  side effects. Cursor advancement can happen only after successful local
  persistence for the relevant step.
- Concurrency: default personal deployment should use one active Steam/demo
  import worker unless a future task proves storage, rate-limit, parser memory
  and DB safety for more.
- Lease/heartbeat: running jobs need reviewable heartbeat or lease evidence so
  stale workers can be distinguished from active work.
- Cancellation/shutdown: cancellation must stop before starting new risky
  phases when possible, preserve retained demo evidence, avoid deleting raw
  demos and write a terminal `cancelled` or `interrupted` result.
- Operator visibility: overview surfaces and reports must show current phase,
  outcome, retryability, cap/safety stop, retained files, cursor mutation and
  whether live Steam/download/parser/evaluator work happened.
- Authorization: a worker implementation does not weaken AGENTS.md. Live Steam,
  parser, evaluator, manual evaluator, service/deploy and production DB work
  still require explicit task authorization.

This plan does not adopt a worker technology, daemon, scheduler, queue library,
service unit, schema change, migration or production deployment.

## Retry Ledger Contract Plan

A future retry ledger must be accepted before cap raise or larger durable
worker operation. It may be implemented in DB schema, JSON, files or another
durable store only through a separate explicit implementation task with the
appropriate schema/data safety scope.

Contract-level retry ledger requirements:

- Attempt tracking: record attempt number, runner identity or mode, started
  time, finished time, outcome, retryability, error code and redacted detail.
- Backoff: retryable external/storage/rate-limit failures require bounded
  backoff with `next_retry_at`; terminal input/parser/schema/auth failures
  must not auto-retry.
- Idempotency keys: every retryable unit must have a stable key derived from
  safe context such as job type, Steam account ID, share-code, demo URL or raw
  demo content identity. Secrets must not be embedded in keys.
- Failure retention: terminal failures must retain enough evidence for operator
  review, including retained raw demo status when a demo exists.
- Cursor safety: failed external calls or failed local persistence must not
  advance Steam cursors. Duplicate-only and no-new outcomes must record their
  cursor decision explicitly.
- Observability: reports and UI/API surfaces must be able to show attempt
  history, last error code, next retry time, current cap and whether the next
  action is automatic, operator-driven or blocked.
- Cleanup boundary: retry ledger work must not delete, move or compress raw
  demos without an explicit storage WP.

Until this ledger is implemented and accepted, retries remain operator-driven
and the one-demo cap remains in force.

## Live Import / Parser / Evaluator Stop Conditions

Stop and report `BLOCKED` before running any command, route, background task or
script if completion would require any of the following without explicit task
authorization:

- live Steam/Valve API, Game Coordinator or demo URL calls;
- demo download, `.dem.bz2` decompression, raw demo copy or parser-backed DEM
  import on production data;
- CSV/JSON/manual upload import into the production DB;
- automatic evaluator or manual evaluator against the production DB;
- import worker, retry worker, queue runner or stale-job repair on production
  data;
- production DB mutation, copied-DB experiment, schema/model/startup/migration
  change or schema artifact update;
- raw demo deletion, movement, compression or cleanup policy change;
- service, systemd, nginx, deploy or runtime configuration change;
- raising `STEAM_IMPORT_MAX_DEMOS_PER_RUN` or bypassing storage/cap guards.

When live import/parser/evaluator work is explicitly authorized, the task must
also specify the allowed path, cap, production DB authorization status,
backup/SHA requirements, temp directory requirements and report evidence. Shell
service calls that touch Steam/import temp storage must set `TMPDIR`, `TEMP`
and `TMP` to `/opt/jc-coach/data/tmp`.

## Import Safety Declaration For Reports

Any future task involving import, parser, evaluator, manual evaluator, import
cap, production DB/import data, or worker/retry behavior must include an import
safety declaration in its report:

- whether live Steam/Valve calls ran;
- whether demo download, decompression or parser jobs ran;
- whether automatic evaluator or manual evaluator ran;
- whether a worker, queue runner, retry path or stale-job repair ran;
- whether `STEAM_IMPORT_MAX_DEMOS_PER_RUN` changed;
- whether the production DB was touched, with DB SHA evidence when required by
  `AGENTS.md`;
- whether Steam cursors advanced;
- whether raw demos were created, retained, deleted, moved or compressed;
- whether `TMPDIR`, `TEMP` and `TMP` were required and what safe value was used;
- whether tests used mocks, temp paths and temp DBs instead of production
  data;
- if any item is not applicable, the reason tied to task scope.

## Retry / Backoff Policy

Stage 7 does not add a durable scheduler or retry ledger. Current retry policy is operator-driven:

- failed jobs keep `status=failed`, `error_message` and `result_json.sync_outcome`;
- queued jobs can be retried by owner/operator-protected routes;
- no automatic production Steam job was introduced;
- future scheduler work must keep no-new/duplicate/error outcomes distinct and must not advance the cursor after failed external or local writes.

## Known Risks

- Service bot cannot enumerate private user history by itself.
- `knowncode=0` is only an initial sentinel when no saved cursor exists; it is not a valid substitute for a latest cursor and can fail.
- Stale cursor can point behind already imported history.
- Valve replay URLs can expire or return transient 502/404/410.
- Durable retry/backoff, scheduler behavior and a sync ledger still need implementation and acceptance before any cap raise.
- One-button live import is accepted for controlled personal use, but `ImportJob.status` remains coarse; use `result_json.overall_outcome/statuses` as the canonical outcome.
- `STEAM_IMPORT_MAX_DEMOS_PER_RUN` remains `1` until worker/retry/result safety is accepted and a separate explicit cap-change WP authorizes the change.
- Uploads/temp still live on root filesystem; a dedicated volume remains recommended.
- Raw demos are retained by policy under `retain_raw_for_parser_development`.
- Parser memory peak should be watched during real demo imports.
- Production job `#15` no longer blocks future one-button queueing.
- Hard process kill can still stop work before in-process interruption marking runs; queue-time stale repair is the durable recovery path.
- Steam OpenID network verification can fail closed if Steam is unreachable.
- Low-level helper `link_steam_account(..., user_id=None)` still supports legacy Steam-only user creation for old service paths; public OpenID callback no longer uses this path without owner.

## Product Rule

Do not turn Steam import into manual share-code entry for every match. The target UX is one-time onboarding plus background sync with clear cursor freshness diagnostics.
