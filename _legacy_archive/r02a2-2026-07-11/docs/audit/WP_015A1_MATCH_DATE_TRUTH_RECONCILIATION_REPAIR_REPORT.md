# WP-015A1 Match Date Truth Reconciliation Repair Report

Date: 2026-07-04

## RESULT: REPAIRED

WP-015A1 performed a controlled production DB metadata repair for historical match-date truth. The repair preserved all rows, did not reset/resync the DB, did not run live Steam/API work, did not run parser jobs, did not change schema, and did not delete/move demo files.

## Backup Path

`data/manual_backups/cs2_coach_before_wp015a1_date_truth_repair_20260704_194655.db`

## DB SHA Before/After

- Before: `e801164c9370d1b4c98bb63cb77c78b026df23a5183f631d8dbafc862f5e391c`
- Backup: `e801164c9370d1b4c98bb63cb77c78b026df23a5183f631d8dbafc862f5e391c`
- After: `8811b08c3e15348ab60ee022887c90ecbe4a17b4bef8ea5d035c083d8f2b6f1c`

## Dry-Run Summary

Planned changes were limited to match ids `1-8, 21-24, 37-38, 59`.

| Rows | Action | Evidence | Playable |
|---|---|---|---|
| `21-24` | Backfill `Match.played_at` and `raw_json` to exact Steam GC match time. | Exactly one linked `steam_history` row for each demo row: `21->5`, `22->6`, `23->7`, `24->8`; linked rows contain `steam_metadata.match_time` with `steam_gc_match_time`. | yes |
| `1-8, 59` | Normalize placeholder `raw_json.match_date_status/source` only. | Existing `steam_metadata.match_time` and `played_at_source=steam_gc_match_time`. | no, `source="steam_history"` |
| `37-38` | Mark existing playable date as approximate/file-modified fallback in `raw_json` only. | No share code or Steam GC metadata/link in current DB raw_json. | yes |

Rows `9-20` and `69` already had exact placeholder metadata but remain `source="steam_history"` with `Match.played_at` null; they were not changed. Rows `39-58` and `60-68` still require future explicit Steam metadata recovery if exact truth is needed; they were not changed.

## Rows Changed

Only these `matches` rows changed:

- `1-8`: `raw_json` only.
- `21-24`: `played_at` and `raw_json`.
- `37-38`: `raw_json` only.
- `59`: `raw_json` only.

Backup/current comparison found changed match ids `[1,2,3,4,5,6,7,8,21,22,23,24,37,38,59]` and unchanged match row count `70`.

## Rows Not Changed And Why

- `9-20, 69`: already exact metadata placeholders; kept non-playable and did not set `Match.played_at`.
- `39-58, 60-68`: no safe exact metadata in current DB/files; future explicit Steam GC/API recovery needed if desired.
- All demo files and storage paths: untouched by this WP.

## Files Changed

- `data/cs2_coach.db`: controlled metadata repair after backup.
- `docs/audit/WP_015A1_MATCH_DATE_TRUTH_RECONCILIATION_REPAIR_REPORT.md`
- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_CONTROL.md`
- `docs/STEAM_IMPORT.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`

## Exact Playable Count Before/After

- Before: 13 exact playable rows (`25-36, 70`).
- After: 17 exact playable rows (`21-36, 70`).

## Approximate Playable Count Before/After

- Before: 6 approximate playable rows (`21-24, 37-38`).
- After: 2 approximate playable rows (`37-38`).

## Unknown/Inconsistent Placeholder Count Before/After

- Before: 38 unknown `steam_history` placeholders; 13 exact-metadata placeholders with null `Match.played_at`.
- After: 29 unknown `steam_history` placeholders; 22 exact-metadata placeholders with null `Match.played_at`.

The 22 exact-metadata placeholders are intentionally non-playable because `source="steam_history"` is excluded from playable match queries.

## Verification

- Total matches: `70`.
- Source breakdown: `steam_history=51`, `demo=19`.
- Playable exact rows after repair: `21-36, 70`.
- Playable approximate rows after repair: `37-38`.
- Playable unknown rows after repair: none.
- Production service remained active.
- No live import/parser process was observed beyond the running uvicorn service.
- `data/uploads`: `3.6G` before/after.
- `data/tmp`: `4.0K` before/after.
- `.dem` file count: `28` before/after.

## Production DB Touched

Yes. Production `data/cs2_coach.db` was intentionally updated after backup and dry-run verification.

## Production Files Touched

No. Demo files and temp/upload storage were not deleted, moved or cleaned.

## Live Import/Parser Run

No.

## Schema Changed

No.

## Full Reset/Resync Performed

No.

## Remaining Risks

- Rows `39-58` and `60-68` remain `steam_history` placeholders without exact normalized date truth and require explicit future Steam GC/API metadata recovery if they need exact dates.
- Placeholder rows with exact metadata still have null `Match.played_at` by design; metrics must continue to exclude `source="steam_history"` from playable match sets.
- Rows `37-38` remain approximate and must not be treated as exact in recent-window metrics, trend windows or freshness logic.
- Broader WP-015 metric formula correctness and parser fact confidence still need dedicated fixture validation.

## Whether WP-015 Metrics Correctness Can Start

Yes. WP-015 can start with the gating rule that exact date metrics use only playable rows whose `raw_json.match_date_status` is `exact_match_date_available` and `raw_json.match_date_source` is `steam_gc_match_time`; approximate rows must be labeled or excluded depending on the metric.
