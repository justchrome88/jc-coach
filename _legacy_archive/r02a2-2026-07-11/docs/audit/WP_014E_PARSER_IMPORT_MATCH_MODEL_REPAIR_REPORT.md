# WP-014E Parser Import Match Model Compatibility Repair Report

Date: 2026-07-04

## RESULT: REPAIRED

WP-014E repaired the parser/import crash observed in WP-014C3:

```text
'played_at_source' is an invalid keyword argument for Match
```

No live Steam/Valve import was run. No one-button import was clicked. No production parser job was run. No production DB mutation, schema change, demo cleanup, file deletion or file move was performed.

## Root Cause

`app.services.steam_match_metadata.apply_steam_metadata_to_parsed_demo()` correctly annotates parsed Steam demo payloads with exact date-source metadata:

- top-level `played_at_source`;
- `parsed["match"]["played_at_source"]`.

`app.services.demo_parser.import_demo_file()` then passed the whole `parsed["match"]` dictionary into `Match(**match_data)`. `app.db.models.Match` has a `played_at` column, but it does not have a `played_at_source` column, so SQLAlchemy rejected the constructor keyword.

## Schema Changed

No.

No schema migration is required for this repair. WP-014B2 established date-source truth as payload metadata, not as a required `matches` table column. Keeping the source truth in `matches.raw_json` and Steam result JSON preserves exact-date semantics without expanding the SQL schema.

## Where `played_at_source` Was Coming From

`played_at_source` is produced by:

- `app/services/demo_parser.py` for parser-derived date source (`demo_header` or `file_modified_fallback`);
- `app/services/steam_match_metadata.py` for Steam GC exact match time (`steam_gc_match_time`);
- `app/services/steam_demo_downloader.py` and `app/services/steam_integration.py` for Steam result/status payloads and exact-date truth reporting.

The crash path was Steam metadata mutating `parsed["match"]`, followed by `Match(**match_data)`.

## Date Source Truth Representation

Date-source truth is now represented as:

- `matches.played_at`: exact timestamp only when the import policy allows it;
- `matches.raw_json`: parser/Steam metadata including `played_at_source`, `match_date_status` and `match_date_source`;
- import job/result JSON: status-level date truth such as `exact_match_date_available` or `exact_match_date_unavailable`.

`played_at_source` remains intentionally outside the `matches` SQL columns.

## Files Changed

- `app/services/demo_parser.py`
- `tests/test_demo_parser.py`
- `docs/STEAM_IMPORT.md`
- `docs/DEMO_STORAGE_TZ.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_CONTROL.md`
- `docs/CURRENT_STATUS.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/audit/WP_014E_PARSER_IMPORT_MATCH_MODEL_REPAIR_REPORT.md`

## Repair Summary

`import_demo_file()` now builds ORM constructor data by filtering parsed match payload keys to real `Match` table columns before creating or updating a `Match` row. Non-column metadata is still retained in the raw parsed payload stored in `matches.raw_json`.

This fixes the C3 regression without weakening WP-014B2 exact match-date truth:

- no fallback file mtime is promoted to exact Steam date;
- Steam GC `match_time` remains the exact source when available;
- unavailable date truth remains explicit in metadata/result payloads.

## Tests Added/Changed

Added parser/import regression coverage in `tests/test_demo_parser.py`:

- Steam metadata with `played_at_source="steam_gc_match_time"` no longer crashes `Match` persistence;
- `played_at_source` is not a `Match` table column;
- exact Steam date source remains in `matches.raw_json`;
- exact-date-unavailable metadata remains in `matches.raw_json`;
- `Match.played_at` can remain `None` for unavailable exact Steam date truth.

Existing Steam import result/status tests were left intact.

## Test Results

```text
APP_ENV=test .venv/bin/pytest tests -q
193 passed, 1 warning in 12.98s

.venv/bin/ruff check .
All checks passed!
```

## DB SHA Before/After

Before:

```text
b8b98a3f79d31020dbb4e3c9bb9dba1a47d03371095dfc08fac87bf15010fda0  data/cs2_coach.db
```

After:

```text
b8b98a3f79d31020dbb4e3c9bb9dba1a47d03371095dfc08fac87bf15010fda0  data/cs2_coach.db
```

## Production Safety

- Production DB touched: no.
- Production files deleted/moved: no.
- Live Steam/import/parser jobs run: no.
- Schema changed: no.
- Production retained C3 demo parsed in this WP: no.

## Remaining Risks

- WP-014E is a mocked/local repair. It proves the constructor mismatch is fixed but does not itself prove the full live Steam path completes.
- The retained WP-014C3 demo remains in `data/uploads` for parser development and operator-controlled future work.
- v0.6 remains blocked until a new controlled one-button live acceptance run verifies end-to-end parser/import success or a truthful controlled terminal outcome after this repair.

## Whether WP-014C4 Live Acceptance Can Start

Yes. From the parser/model compatibility perspective, WP-014C4 repeat live acceptance can start after the operator explicitly authorizes live Steam/import/parser work and repeats the normal backup, disk, service and DB SHA preflight gates.
