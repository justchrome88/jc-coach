# WP-014B1 Import Job Truth Status Repair Report

## RESULT

COMPLETED

## Scope

WP-014B1 repaired only Steam import-job truth and status taxonomy. It did not change DB schema, demo cleanup lifecycle, parser behavior or `/coach` UI. No live Steam/Valve import, demo download or production parser job was run.

## Files Changed

- `app/services/steam_integration.py`
- `tests/test_steam_integration.py`
- `docs/STEAM_IMPORT.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_CONTROL.md`
- `docs/CURRENT_STATUS.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/audit/WP_014B1_IMPORT_JOB_TRUTH_STATUS_REPAIR_REPORT.md`

## Statuses Added / Standardized

`steam_import_all` and tracked exact share-code import now report these statuses in `ImportJob.result_json.statuses`:

- `success`
- `no_new`
- `need_code`
- `steam_not_connected`
- `rate_limited`
- `download_failed`
- `parser_failed`
- `partial_success`
- `duplicate_skipped`
- `exact_match_date_available`
- `exact_match_date_unavailable`

The aggregate result also records:

- `overall_outcome`
- `status_summary`
- `clean_success`
- `error_message`
- `job_status_limitation`

## Behavior Changed

- `/settings/imports/pull-all` still queues `steam_import_all` before background work. The primary one-button path keeps existing background behavior.
- `steam_import_all` no longer records clean `succeeded` for disconnected Steam, missing auth/cursor, download failure, parser failure or partial success.
- Clean outcomes may still use `ImportJob.status=succeeded` for `success`, `no_new` and `duplicate_skipped`.
- Partial success is represented as `result_json.overall_outcome=partial_success` and persisted as `ImportJob.status=failed`, because the existing model has no `partial_success` status and this WP did not change schema.
- Exact share-code import now creates a `share_code_import` job and marks it `running` before downloader/parser work can start.
- Exact share-code import remains a non-primary debug/manual path and records `primary_path=false` in its result.
- Stale production queued jobs were not mutated; cleanup remains a separate operator action.

## Tests Added / Changed

Mocked tests were added/updated in `tests/test_steam_integration.py` for:

- missing Steam account -> `steam_not_connected`;
- missing auth code/cursor -> `need_code`;
- no-new -> `no_new`;
- duplicate-only -> `duplicate_skipped`;
- download failure -> `download_failed`;
- parser failure -> `parser_failed`;
- partial import -> `partial_success`;
- aggregate job is not clean success when inner failures exist;
- exact share-code path creates a tracking job before downloader work.

All Steam/API/download behavior in these tests is mocked.

## Test Results

Targeted pre-check:

```bash
APP_ENV=test .venv/bin/pytest tests/test_steam_integration.py tests/test_steam_cursor_truth.py -q
```

Result: `37 passed`.

Final checks:

```bash
APP_ENV=test .venv/bin/pytest tests -q
```

Result: `163 passed, 1 warning`.

```bash
.venv/bin/ruff check .
```

Result: `All checks passed!`

```bash
git diff --check
```

Result: passed.

```bash
python3 scripts/project_gate.py postflight
```

Result: passed.

## DB SHA

- Before: `be2a54fef35227129ae2023931e76d2cf20e100ae09d9ec7e7477f1755526fc2`
- After final checks: `be2a54fef35227129ae2023931e76d2cf20e100ae09d9ec7e7477f1755526fc2`

Production DB was not touched.

## Production DB Touched

No.

## Live Steam / Import / Parser Jobs Run

No.

Only mocked tests were run. No live Steam/Valve import, demo download or production parser job was started.

## Schema Changed

No.

## Remaining Risks

- Demo cleanup lifecycle is still not accepted: persisted raw `.dem` cleanup after successful parse/persist remains open.
- Failed-demo quarantine/cleanup-policy-needed state remains open.
- `ImportJob.status` still has only `queued`, `running`, `succeeded` and `failed`; partial success is encoded in `result_json` and persisted as `failed`.
- Stale production queued jobs remain untouched and require a separate operator-safe cleanup action.
- No live Steam runtime acceptance was performed in this WP.

## Whether WP-014B2 Can Start

yes
