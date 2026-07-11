# WP-014D2 Parent Checkpoint and Interruption Repair Report

Date: 2026-07-04

RESULT: REPAIRED

## Scope

Minimal repair for Steam `steam_import_all` parent job progress and stale/interrupted handling. This WP did not run live Steam/Valve import, did not download production demos, did not run production parser jobs, did not mutate the production DB, did not delete or move production demo files, did not change schema and did not commit.

## Files Changed

- `app/config.py`
- `app/main.py`
- `app/api/routes.py`
- `app/web/routes.py`
- `app/services/steam_integration.py`
- `app/services/steam_demo_downloader.py`
- `scripts/repair_stale_steam_import_job.py`
- `tests/test_steam_integration.py`
- `docs/STEAM_IMPORT.md`
- `docs/DEMO_STORAGE_TZ.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_CONTROL.md`
- `docs/CURRENT_STATUS.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/audit/WP_014D2_PARENT_CHECKPOINT_INTERRUPTION_REPORT.md`

## Checkpoint Behavior

Parent `steam_import_all` jobs now persist compact `result_json.progress` checkpoints during the run. Checkpoints include:

- `phase`
- `updated_at`
- counters: `processed`, `imported`, `failed`, `skipped`, `pending`
- `child_job_ids`
- current share code when available
- compact storage budget summary
- bounded `recent_events` capped at 25 entries

Implemented checkpoint phases include:

- `started`
- `account_checked`
- `share_codes_fetch_started`
- `share_codes_fetched`
- `demo_queued`
- `demo_downloading`
- `demo_downloaded`
- `demo_decompressing`
- `demo_stored`
- `parser_started`
- `parser_succeeded`
- `parser_failed`
- `disk_budget_exceeded`
- `batch_cap_reached`
- `interrupted`

The terminal parent result preserves the last progress payload, so a completed/failed job still exposes the final checkpoint trail without unbounded JSON growth.

## Stale / Interrupted Job Behavior

New settings:

- `STEAM_IMPORT_STALE_RUNNING_JOB_SECONDS`, default `3600`
- `STEAM_IMPORT_REPAIR_STALE_ON_STARTUP`, default `false`

Queue-time behavior:

- Before creating or returning a parent one-button import, the service scans running `steam_import_all` jobs.
- Running jobs older than the configured timeout are marked `failed` with `result_json.overall_outcome = "interrupted"` and `statuses = ["interrupted"]`.
- Non-stale running jobs are still treated as current/blocking and are not replaced.
- Stale jobs are not silently reused as current.

Startup behavior:

- Startup stale repair is implemented but disabled by default.
- Operators may enable it with `STEAM_IMPORT_REPAIR_STALE_ON_STARTUP=true`, but the safer default for production is explicit operator repair.

Best-effort in-process interruption:

- API and web background wrappers catch `BaseException`, mark the selected running parent job interrupted if possible, then re-raise.
- This cannot handle `SIGKILL`; queue-time stale repair remains the durable recovery path after hard process death.

## Operator Repair Helper

Added explicit helper:

```bash
python3 scripts/repair_stale_steam_import_job.py --job-id 15 --i-have-backup --confirm-interrupt
```

Safety properties:

- Requires explicit `--job-id`.
- Requires `--i-have-backup`.
- Requires `--confirm-interrupt`.
- Refuses non-`steam_import_all` jobs.
- Refuses jobs that are not `running`.
- Refuses jobs that are not stale by the configured timeout.
- Updates only the selected job.

Production job `#15` was not mutated in this WP.

## Tests Added / Changed

Added mocked/local coverage in `tests/test_steam_integration.py` for:

- parent checkpoint persists after account check;
- checkpoint persists after child sync success;
- checkpoint persists before demo download;
- disk-budget checkpoint persists;
- stale running parent is not reused;
- stale running parent can be marked interrupted;
- non-stale running parent remains blocking/current;
- startup stale repair is opt-in;
- recent checkpoint events are bounded.

Existing Steam import and storage guard tests remain mocked/local; no live Steam calls are part of this WP.

## Verification

Initial production DB SHA before changes:

```text
8b0799d7da12230018a02a88031006f95e68cf7f3193d4b55d925ead5d3648b0  data/cs2_coach.db
```

Targeted check run during implementation:

```text
APP_ENV=test .venv/bin/pytest tests/test_steam_integration.py -q
51 passed
```

Final required checks:

```text
APP_ENV=test .venv/bin/pytest tests -q
191 passed, 1 warning

.venv/bin/ruff check .
All checks passed.

git diff --check
passed

python3 scripts/project_gate.py postflight
passed; DB SHA unchanged

sha256sum data/cs2_coach.db
8b0799d7da12230018a02a88031006f95e68cf7f3193d4b55d925ead5d3648b0  data/cs2_coach.db
```

## DB / Runtime Safety

- Production DB touched: no
- Job `#15` mutated: no
- Production files deleted/moved: no
- Live Steam/import/parser jobs run: no
- Schema changed: no
- Commit made: no

## Remaining Risks

- Production job `#15` is still stale until an explicit operator repair step is authorized and run.
- Hard kill cannot be caught in-process; stale recovery relies on queue-time repair or explicit operator repair.
- WP-014D1/D2 repairs have mocked/local coverage only. Repeat live one-button acceptance remains required before promoting Steam import to `v0.6`.
- Startup stale repair is opt-in to avoid surprise production DB mutation on service restart.

## Next Step

WP-014D3 can start as an operator-controlled step: back up production DB, record DB SHA, explicitly mark job `#15` interrupted with the repair helper, verify only job `#15` changed, then prepare a repeat live acceptance run under the existing disk/batch/checkpoint guards.
