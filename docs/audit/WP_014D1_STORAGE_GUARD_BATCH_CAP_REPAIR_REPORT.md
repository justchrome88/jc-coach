# WP-014D1 Storage Guard and Batch Cap Repair Report

Date: 2026-07-04

## RESULT

COMPLETED

## Scope

Minimal runtime/storage safety repair only:

- disk budget/preflight;
- demo batch cap;
- per-job byte budget;
- per-demo byte budget;
- streaming download with byte counting;
- budget-aware result statuses.

Out of scope and not performed:

- live Steam/Valve import;
- production demo download;
- production parser job;
- production DB mutation;
- production demo file delete/move;
- job `#15` stale-running repair;
- parent checkpoint/interruption/shutdown repair;
- schema change;
- commit.

## Files Changed

- `.env.example`
- `app/config.py`
- `app/services/demo_parser.py`
- `app/services/steam_demo_downloader.py`
- `app/services/steam_integration.py`
- `app/services/steam_storage_guard.py`
- `tests/conftest.py`
- `tests/test_steam_integration.py`
- `tests/test_steam_storage_guard.py`
- `docs/STEAM_IMPORT.md`
- `docs/DEMO_STORAGE_TZ.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_CONTROL.md`
- `docs/CURRENT_STATUS.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/audit/WP_014D1_STORAGE_GUARD_BATCH_CAP_REPAIR_REPORT.md`

Existing staged diagnosis report from WP-014D remained present:

- `docs/audit/WP_014D_STEAM_IMPORT_RUNTIME_STORAGE_SAFETY_DIAGNOSIS.md`

## Settings Added / Defaults

Added to `Settings` and documented in `.env.example`:

- `STEAM_IMPORT_MAX_DEMOS_PER_RUN=1`
- `STEAM_IMPORT_MAX_BYTES_PER_JOB=2147483648` (`2 GiB`)
- `STEAM_IMPORT_MAX_SINGLE_DEMO_BYTES=629145600` (`600 MiB`)
- `STEAM_IMPORT_MIN_FREE_BYTES=8589934592` (`8 GiB`)
- `STEAM_IMPORT_PRESERVE_FREE_BYTES=5368709120` (`5 GiB`)
- `STEAM_IMPORT_UNKNOWN_DEMO_RESERVE_BYTES=1610612736` (`1.5 GiB`)

Pytest overrides these to small safe values in `tests/conftest.py` so tests do not depend on host `/tmp` capacity.

## Storage Guard Behavior

Added `app/services/steam_storage_guard.py`.

The guard:

- resolves upload dir and temp dir to real paths;
- reads filesystem capacity with `shutil.disk_usage()`;
- exposes structured budget snapshots for result JSON;
- checks parent preflight before a new `steam_import_all` starts;
- checks before selecting/downloading each demo;
- checks Content-Length when available;
- checks before temp download writes;
- checks before `.bz2` decompression writes;
- checks before copying to `data/uploads`;
- tracks downloaded, decompressed and stored bytes;
- raises `SteamStorageBudgetExceeded` with first-class status and structured budget data.

## Batch Cap Behavior

`steam_import_all` no longer reuses `steam_sync_max_codes` as the demo download count.

The one-button path passes `STEAM_IMPORT_MAX_DEMOS_PER_RUN` to `download_pending_steam_demos()`. The downloader also clamps its selected rows to the guard's max demos per run. Unselected pending rows remain pending, not failed, and result JSON includes:

- `batch_cap_reached`;
- `remaining_pending`;
- `storage_budget`.

## Per-Job / Per-Demo Budget Behavior

The downloader stops before starting the next demo when the configured job byte budget would be exceeded by the unknown-size reserve or known size.

If `Content-Length` exceeds `STEAM_IMPORT_MAX_SINGLE_DEMO_BYTES`, that demo fails with `demo_too_large`. If size is unknown, the guard reserves `STEAM_IMPORT_UNKNOWN_DEMO_RESERVE_BYTES` before starting the demo.

Budget failures produce these statuses where relevant:

- `disk_budget_exceeded`;
- `batch_cap_reached`;
- `demo_too_large`;
- `storage_preflight_failed`.

Existing statuses continue to work:

- `success`;
- `no_new`;
- `partial_success`;
- `download_failed`;
- `parser_failed`.

## Download Streaming Behavior

`_download_demo_file()` no longer buffers the full response body with `response.read()` into memory. It streams response chunks to disk with byte counting and guard checks.

`.bz2` decompression now uses `bz2.BZ2Decompressor()` over file chunks and writes decompressed chunks to the temp `.dem`, with per-chunk byte counting and budget checks.

## Tests Added / Changed

Added `tests/test_steam_storage_guard.py` covering:

- preflight passes with enough free space;
- preflight fails below min free;
- preserve-free hard floor blocks operation;
- unknown-size reserve uses configured bytes.

Updated `tests/test_steam_integration.py` covering:

- batch cap prevents downloading all pending demos;
- remaining demos stay pending, not failed;
- import result includes `batch_cap_reached`;
- Content-Length blocks too-large demo;
- per-job byte budget stops before the next demo;
- streamed `.dem` download writes chunks and counts bytes;
- streamed `.bz2` decompression writes chunks and counts bytes.

Existing Steam/parser/storage tests were kept mocked/local. No live Steam, demo download or production parser job was run.

## Test Results

Targeted tests:

```bash
APP_ENV=test .venv/bin/pytest tests/test_steam_storage_guard.py tests/test_steam_integration.py tests/test_demo_parser.py tests/test_demo_storage.py -q
```

Result: `58 passed`.

Full tests:

```bash
APP_ENV=test .venv/bin/pytest tests -q
```

Result: `182 passed, 1 warning`.

Ruff:

```bash
.venv/bin/ruff check .
```

Result: `All checks passed!`

Final gate commands are recorded in the user-facing final response for this WP.

## DB SHA

- Before repair: `8b0799d7da12230018a02a88031006f95e68cf7f3193d4b55d925ead5d3648b0`
- After tests/final checks: `8b0799d7da12230018a02a88031006f95e68cf7f3193d4b55d925ead5d3648b0`

## Production DB Touched

No.

Tests used `APP_ENV=test` and isolated test DB settings from `tests/conftest.py`.

## Production Files Deleted / Moved

No.

No files under `data/uploads` or `data/incoming_demos` were deleted or moved.

## Live Steam / Import / Parser Jobs Run

No.

All Steam/download/parser behavior was mocked or local temp-file based.

## Schema Changed

No.

## Remaining Risks

- Parent `steam_import_all` progress is still only terminal, not incrementally checkpointed.
- Stale production job `#15` remains `running` with null `result_json`; this WP did not mutate it.
- Graceful shutdown/interruption handling is not repaired.
- Storage guards are covered by mocked/local tests but have not yet been proven by a repeat live acceptance.
- `data/uploads` still lives on root filesystem; a dedicated volume or bind mount remains recommended before long retain-raw parser work.

## Whether WP-014D2 Parent Checkpoints / Interruption Repair Can Start

yes
