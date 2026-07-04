# WP-014F Promote Import Acceptance to v0.6 Report

Date: 2026-07-04

## RESULT: PROMOTED

WP-014F promoted controlled personal import acceptance from `v0.5` to `v0.6` based on WP-014C4 `PASS_WITH_WARNINGS`.

This WP was documentation/status only. No code, tests, schema, production DB data, live import, parser job or demo file lifecycle action was changed.

## Previous Version

`v0.5`

## New Version

`v0.6`

## Acceptance Basis

Acceptance basis: `docs/audit/WP_014C4_REPEAT_ONE_BUTTON_LIVE_ACCEPTANCE_AFTER_PARSER_REPAIR_REPORT.md`

WP-014C4 validated the real one-button Steam import path after the WP-014D safety repairs and WP-014E parser/model repair:

- one authorized click;
- TMPDIR resolved to `/opt/jc-coach/data/tmp`;
- storage preflight passed;
- batch cap limited the run to exactly one demo;
- parser/import succeeded;
- exact date truth persisted via `steam_gc_match_time`;
- parent job reached terminal non-running state with truthful `result_json`;
- service stayed healthy;
- disk growth was bounded.

## Warnings Carried Forward

- `ImportJob.status` remains coarse and may be `failed` for non-clean terminal outcomes such as `batch_cap_reached`; canonical truth is `result_json.overall_outcome/statuses`.
- `data/uploads` and `data/tmp` still live on the root filesystem; a dedicated volume/bind mount remains recommended.
- Raw demos are retained by policy under `retain_raw_for_parser_development`.
- Parser memory peak should be watched during real demo imports.
- Friends/public readiness remains blocked by broader security, ownership, migration, backup and observability gates.

## Files Changed

- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_CONTROL.md`
- `docs/STEAM_IMPORT.md`
- `docs/DEMO_STORAGE_TZ.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/project_management/VERSION_ROADMAP.md`
- `docs/audit/WP_014F_PROMOTE_IMPORT_ACCEPTANCE_TO_V0_6_REPORT.md`

`docs/README.md` and `docs/project_management/DOCS_INDEX.md` were checked for current version/status language and did not require updates.

## Code Changed

No.

## DB Touched

No.

Production DB SHA observed during preflight:

```text
e801164c9370d1b4c98bb63cb77c78b026df23a5183f631d8dbafc862f5e391c  data/cs2_coach.db
```

## Live Import Run

No.

## Parser Run

No.

## Production Files Deleted/Moved

No.

## Remaining Risks

- `v0.6` is controlled personal import acceptance, not friends/public readiness.
- Root-filesystem storage is still a deployment risk even with runtime guards.
- Retain-raw policy continues to accumulate demo files over time.
- Import status enum remains less expressive than the result taxonomy.
- Parser metric confidence and correctness still need deeper validation before metric-driven coaching can be treated as trusted.

## Next Recommended WP

`WP-015 Metrics Correctness` targeting `v0.7`.

Do not start WP-015 without an explicit new WP prompt.
