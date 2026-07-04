# WP-014B2 Exact Match Date Truth Report

## RESULT

COMPLETED

## Scope

WP-014B2 repaired only exact match-date truth for the Steam import path. It did not change DB schema, demo cleanup lifecycle, parser internals or production data. No live Steam/Valve import, demo download or production parser job was run.

## Files Changed

- `app/services/steam_integration.py`
- `app/services/steam_demo_downloader.py`
- `app/web/routes.py`
- `app/templates/matches.html`
- `app/templates/match_detail.html`
- `app/templates/import_settings.html`
- `tests/test_steam_integration.py`
- `docs/STEAM_IMPORT.md`
- `docs/METRICS.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_CONTROL.md`
- `docs/CURRENT_STATUS.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/audit/WP_014B2_EXACT_MATCH_DATE_TRUTH_REPORT.md`

## Date Truth Behavior Changed

- Primary Steam import treats Steam GC `match_time` / `steam_gc_match_time` as the only exact Steam match date source.
- Valid Steam GC `match_time` is normalized and stored in `Match.played_at`.
- Missing Steam GC `match_time` is recorded as `exact_match_date_unavailable`.
- Primary Steam import without GC `match_time` clears imported `Match.played_at` instead of leaving parser/file-mtime fallback as canonical match date.
- `raw_json` and import result payloads record `match_date_status`, `match_date_source` and a truth note.
- Aggregate import results now distinguish:
  - `exact_match_date_available`;
  - `exact_match_date_unavailable`;
  - `approximate_match_date`.
- Steam freshness now uses only exact imported Steam dates. Detectable manual/parser/file-mtime fallback dates do not silently block new Steam imports.
- Match list/detail UI now labels date truth as exact, approximate or unknown instead of implying every displayed date is exact.

## Fields / Source Of Truth Used

- Canonical datetime field: `Match.played_at`.
- Exact Steam source: Steam GC `match_time`, normalized as `steam_gc_match_time`.
- Date truth metadata without schema change:
  - `Match.raw_json.played_at_source`;
  - `Match.raw_json.match_date_status`;
  - `Match.raw_json.match_date_source`;
  - `Match.raw_json.steam_metadata`;
  - `ImportJob.result_json.statuses`;
  - `ImportJob.result_json.latest_imported_played_at_source_policy`.
- Technical timestamps that must not be treated as exact match date:
  - `import_jobs.created_at`;
  - `matches.created_at`;
  - `download/import imported_at`;
  - `DemoParseArtifact.parsed_at`;
  - file mtime / `file_modified_fallback`.

## Tests Added / Changed

Mocked tests were added/updated in `tests/test_steam_integration.py` for:

- valid Steam GC `match_time` becomes exact imported `Match.played_at`;
- missing Steam GC `match_time` becomes `exact_match_date_unavailable`;
- file-mtime fallback is cleared for primary Steam import and is not treated as exact;
- aggregate job/result JSON exposes exact/unavailable/approximate date statuses;
- Steam freshness ignores approximate/manual/file-mtime fallback dates.

All Steam/API/download/parser behavior in these tests is mocked.

## Test Results

Targeted pre-check:

```bash
APP_ENV=test .venv/bin/pytest tests/test_steam_integration.py tests/test_steam_cursor_truth.py tests/test_web_smoke.py -q
```

Result: `57 passed, 1 warning`.

Final checks:

```bash
APP_ENV=test .venv/bin/pytest tests -q
```

Result: `167 passed, 1 warning`.

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

- Demo cleanup lifecycle is still not accepted and remains WP-014B3.
- Failed-demo quarantine/cleanup-policy-needed state remains open.
- Date truth is stored in `raw_json`/`result_json`; a future schema migration may be useful for first-class querying.
- Manual demo upload can still use parser/demo header or file-mtime fallback as approximate/manual date evidence; it is not promoted to exact for Steam freshness.
- No live Steam runtime acceptance was performed in this WP.

## Whether WP-014B3 Demo Cleanup Can Start

yes
