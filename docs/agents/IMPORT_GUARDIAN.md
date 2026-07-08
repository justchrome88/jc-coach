# Import Guardian

Last updated: 2026-07-08.

## Scope

Protects Steam import, manual demo import, parser jobs, evaluator/manual
evaluator paths when driven by import data, upload routes, service-bot
boundaries, import caps, durable worker plans and retry-ledger plans.

## Activation Paths

- `app/services/steam_integration.py`
- `app/services/demo_parser.py`
- `app/services/steam_demo_downloader.py`
- `app/services/steam_storage_guard.py`
- import/upload routes
- Steam/import/parser docs and tests
- import worker, retry, queue and stale-job repair docs or code
- `data/uploads/*`
- `data/incoming_demos/*`

## Forbidden Actions

- Running live Steam calls without explicit authorization.
- Running production import/parser jobs during governance/tooling work.
- Downloading or parsing real demos unless the WP allows it.
- Running evaluator or manual evaluator jobs on production import data unless
  the WP allows it.
- Raising `STEAM_IMPORT_MAX_DEMOS_PER_RUN` or bypassing cap/storage guards
  without an explicit cap-change WP.
- Implementing or running durable import workers, retry workers, queue runners
  or stale-job repair unless explicitly scoped.
- Storing Steam personal credentials, refresh tokens or Steam Guard data.
- Advancing Steam cursor outside an authorized import flow.
- Deleting, moving or compressing raw demos without explicit storage scope.

## Required Checks

- Mocked/import-safe tests only unless live work is explicitly authorized.
- DB SHA evidence according to `AGENTS.md` when production DB/import data could
  be affected.
- Review `docs/STEAM_IMPORT.md` for Steam scope.
- Preserve `STEAM_IMPORT_MAX_DEMOS_PER_RUN=1` unless a separate cap-change WP
  authorizes a change.
- `git diff --check`.

## Evidence Required

- Statement whether live Steam/import/parser jobs ran.
- Statement whether evaluator/manual evaluator jobs ran.
- Statement whether worker, queue, retry or stale-job repair paths ran.
- Statement whether the import cap changed.
- Cursor mutation status when Steam paths are involved.
- DB touch status.
- Raw demo creation/retention/delete/move/compress status.
- Temp directory status when Steam/import shell service calls run.
- Mock/live boundary used for tests.
- `result_json` outcome/retryability evidence for import jobs when jobs are
  inspected or executed.

## Escalation / Blocker Rules

Block if a task would require live Steam, demo download, parser execution,
evaluator/manual evaluator execution, worker/retry execution, import cap
change, production DB writes, schema changes, copied-DB work, service/deploy
changes or raw demo cleanup without explicit permission.
