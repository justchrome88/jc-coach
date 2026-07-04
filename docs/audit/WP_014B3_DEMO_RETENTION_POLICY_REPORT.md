# WP-014B3 Demo Retention Policy Report

## RESULT

COMPLETED

## Scope

WP-014B3 made demo retention policy explicit and added metadata/tests around file/DB consistency. It did not enable automatic delete-after-success, did not delete production demo files, did not change schema, did not rewrite parser logic and did not run live Steam/import/parser jobs.

## Demo Lifecycle Inventory

- Steam temp download directory: `tempfile.mkdtemp(prefix="jc-steam-demo-")` in `app/services/steam_demo_downloader.py`.
- Downloaded archive path: temp dir `<share_code>.dem.bz2` when Valve returns compressed demo.
- Decompressed temp `.dem` path: temp dir `<share_code>.dem`.
- Persisted raw demo path: `data/uploads/<timestamp>_<sha>_<filename>` through `app/services/demo_parser.py::_store_demo()`.
- Raw copy timing: `import_demo_file()` copies the raw demo before parser work.
- Parsed persistence:
  - `matches` row with `demo_file` path and `raw_json`;
  - `DemoParseArtifact`;
  - normalized parser tables: rounds, player rounds, weapons, damage events, duels, grenades.
- Steam temp dir cleanup: temp directory is removed after `_download_and_import_match()` returns or fails. Persisted raw copy in `data/uploads` is retained by policy.

## Current Retention Policy

Current policy: `retain_raw_for_parser_development`.

`delete_after_success` is not enabled. Raw demos remain available for parser debugging and reprocessing until parser acceptance is complete.

## Metadata / Result JSON Changes

Successful demo imports now include:

- `demo_retention_policy`;
- `demo_retention_status`;
- `raw_demo_path`;
- `raw_demo_size_bytes`;
- `parser_success`.

Default successful status: `retained_for_parser_dev`.

Parser/download failures carry retention metadata when available:

- `retained_after_failure` when the stored raw demo is known and retained;
- `cleanup_needed` when the raw demo state requires operator review.

Steam placeholder `raw_json` and download result rows now include the retention metadata when available.

## File/DB Consistency Helper

Added: yes.

`app/services/demo_storage.py::classify_demo_file_consistency()` classifies demo file state without mutation:

- `db_references_file_and_file_exists`;
- `db_references_file_but_file_missing`;
- `file_exists_without_clear_db_reference`;
- `legacy_unknown`.

`demo_storage_report()` includes this classifier under `file_db_consistency`.

## Future Delete-After-Success Mode

A disabled helper exists for future mode:

- `app/services/demo_retention.py::delete_raw_demo_after_success()`.

Default call does not delete. Deletion requires explicit `enabled=True` and is covered only with temp-file tests. Production mode remains disabled until parser acceptance.

## Tests Added / Changed

Mocked/local-file tests cover:

- successful import records `retained_for_parser_dev`;
- parser failure records `retained_after_failure`;
- manual/demo parser import remains retain-by-default;
- future delete helper is disabled by default;
- future delete helper deletes only temp test files when explicitly enabled;
- file/DB consistency detects existing, missing and unreferenced demo files;
- Steam parser failure propagates retained-after-failure metadata.

## Test Results

Targeted pre-check:

```bash
APP_ENV=test .venv/bin/pytest tests/test_demo_parser.py tests/test_demo_storage.py tests/test_steam_integration.py -q
```

Result: `48 passed`.

Final checks:

```bash
APP_ENV=test .venv/bin/pytest tests -q
```

Result: `172 passed, 1 warning`.

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

## Production DB Touched

No.

## Production Files Deleted

No.

## Live Steam / Import / Parser Jobs Run

No.

Only mocked/local-file tests were run. No live Steam/Valve import, demo download or production parser job was started.

## Schema Changed

No.

## Remaining Risks

- Parser acceptance is still incomplete; raw demo retention remains the correct default.
- Retention metadata is stored in `raw_json`/`result_json`, not first-class columns.
- Legacy existing rows may still have `unknown_legacy` retention state until reimported or audited.
- Future delete-after-success mode needs a separate production acceptance WP after parser payload verification.
- No live one-button Steam acceptance was performed in this WP.

## Whether WP-014C One-Button Live Acceptance Can Start

yes, with explicit authorization, backup/DB SHA evidence, and live-job boundaries.
