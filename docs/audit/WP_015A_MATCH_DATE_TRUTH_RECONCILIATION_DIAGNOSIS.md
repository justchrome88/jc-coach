# WP-015A Match Date Truth Reconciliation Diagnosis

Date: 2026-07-04

## RESULT: DIAGNOSED

WP-015A diagnosed production match date truth state after promotion to `v0.6`. This pass was read-only except for creating this audit report. No code, tests, schema, production DB rows, live Steam/import/parser jobs, demo files or uploads were changed.

## Product Version Observed

`v0.6`

Observed from `docs/CURRENT_STATUS.md`, `docs/HANDOFF.md`, `docs/PROJECT_CONTROL.md` and `docs/project_management/VERSION_ROADMAP.md`.

## DB SHA

```text
e801164c9370d1b4c98bb63cb77c78b026df23a5183f631d8dbafc862f5e391c  data/cs2_coach.db
```

## Total Match Inventory

Total `matches` rows: `70`.

Playable rows by current code are rows whose `source != "steam_history"`. `app/services/match_queries.py` excludes `steam_history` placeholders from playable match selects.

## Source Breakdown

| source | count | current meaning |
|---|---:|---|
| `demo` | 19 | playable parsed demo/import rows |
| `steam_history` | 51 | non-playable Steam share-code placeholders / history rows |

No `manual`, `upload`, `parser-only` or other source values were present as separate source names. Historical manual/parser-only imports are represented as `source="demo"`.

## Date Truth Breakdown

Classifier used:

- `exact_match_date_available`: `match_date_status=exact_match_date_available`, source `steam_gc_match_time`, and `Match.played_at` present.
- `exact_match_date_unavailable`: explicit unavailable metadata or source `unavailable`.
- `approximate_match_date`: parser/demo date source such as `file_modified_fallback` or `demo_header`.
- `unknown_match_date`: no playable `played_at` and no explicit exact/unavailable/approximate status.
- `legacy/no_status`: `played_at` present but no usable truth metadata and not otherwise classifiable.
- `inconsistent/conflicting_status`: row metadata claims exact but row-level `Match.played_at` is null.

| classification | count | row ids |
|---|---:|---|
| `exact_match_date_available` | 13 | 25-36, 70 |
| `exact_match_date_unavailable` | 0 | none |
| `approximate_match_date` | 6 | 21-24, 37-38 |
| `unknown_match_date` | 38 | 1-8, 39-68 except 69 |
| `legacy/no_status` | 0 | none |
| `inconsistent/conflicting_status` | 13 | 9-20, 69 |

By source:

| source | exact | approximate | unknown | inconsistent |
|---|---:|---:|---:|---:|
| `demo` | 13 | 6 | 0 | 0 |
| `steam_history` | 0 | 0 | 38 | 13 |

## Exact Date Rows

Playable exact rows: `25-36, 70`.

These rows have:

- `source="demo"`;
- `Match.played_at` present;
- `raw_json.match_date_status=exact_match_date_available`;
- `raw_json.match_date_source=steam_gc_match_time`;
- Steam share-code linkage in `demo_file` and/or `raw_json`;
- one corresponding `steam_history` placeholder row.

The newest accepted WP-014C4 row is:

```text
demo row #70
played_at=2026-07-03 19:34:35
raw_json.played_at_source=steam_gc_match_time
raw_json.match_date_status=exact_match_date_available
linked steam_history row #69
```

## Approximate/Unknown Rows

Approximate playable rows: `21-24, 37-38`.

All six have playable `Match.played_at`, but `raw_json.played_at_source=file_modified_fallback`. They are dangerous for date-ordered metrics unless gated.

Unknown placeholder rows: `1-8, 39-68 except 69`.

Notable split:

- Rows `1-8` and `59` are `steam_history` placeholders with `raw_json.steam_metadata.match_time` and `played_at_source=steam_gc_match_time`, but they lack normalized `match_date_status`.
- Rows `39-58` and `60-68` are bare `steam_history` share-code placeholders without existing Steam GC `match_time` in raw JSON.

## Legacy/No-Status Rows

No row fell into a pure `legacy/no_status` bucket after applying current source semantics. The legacy issue appears as:

- approximate playable rows with `file_modified_fallback` and no `match_date_status`;
- `steam_history` placeholders with exact-looking `steam_metadata.match_time` but no normalized `match_date_status`.

## Inconsistent Rows

Rows `9-20` and `69` are `steam_history` placeholders with:

- `raw_json.match_date_status=exact_match_date_available`;
- `raw_json.match_date_source=steam_gc_match_time`;
- `raw_json.played_at` present;
- `Match.played_at` null.

This is inconsistent if every row is judged by `Match.played_at`, but it is not currently dangerous for metrics because `steam_history` is excluded by `playable_match_select()`. It is still worth reconciling or documenting explicitly so storage/UI/reporting does not confuse placeholders with playable matches.

## Recoverable Rows

Recoverable without live Steam/API or parser rerun:

- Rows `1-8, 59`: `steam_history` placeholders already contain Steam GC `match_time` and `played_at`; backfill normalized `match_date_status/source` in `raw_json`.
- Rows `9-20, 69`: placeholders already have exact metadata; repair should clarify placeholder semantics and optionally add explicit `placeholder_date_truth` metadata while leaving them non-playable.
- Rows `21-24`: playable demo rows are approximate/file-mtime, but each raw JSON contains a share code that links to `steam_history` rows `5-8`, which already contain Steam GC `match_time`. These can be safely backfilled to exact from existing DB metadata.

Recoverable only with future live GC/API metadata retrieval:

- Rows `39-58, 60-68`: `steam_history` rows have share codes but no stored `match_time`. They can be resolved later through the existing Steam GC path, under explicit live authorization and storage/batch safeguards. They do not need a full DB reset.

Already exact:

- Rows `25-36, 70`.

## Unrecoverable Rows

Rows `37-38` are playable demo rows with `file_modified_fallback`, no share code in raw JSON or demo file, no Steam metadata and no linked `steam_history` row. They are not safely exact-recoverable from current DB/files without a parser rerun or external metadata that is not currently present.

Recommended handling for rows `37-38`: preserve them, but explicitly mark them `approximate_match_date` / `file_modified_fallback` in a later controlled DB repair, and exclude them from exact-date-dependent metrics.

## Rows Dangerous For Metrics

Immediately dangerous for WP-015 date-ordered metrics:

- Rows `21-24, 37-38`: playable `demo` rows with `Match.played_at` present but only `file_modified_fallback`. These currently sort as dated matches in dashboard/stats/coach/reports because analytics sort by `Match.played_at` and do not require exact date truth.

Secondary risks:

- Rows `25-36, 70`: exact playable rows are logically linked to `steam_history` placeholders. This is expected, and placeholders are excluded from playable metrics, but linkage should remain explicit.
- Rows `9-20, 69`: placeholders have exact raw date metadata but null `Match.played_at`; safe for metrics today, but potentially confusing in storage/import reports.

Current code risk:

- `playable_match_select()` only filters out `steam_history`.
- `analytics._sort_matches()`, `aim_stats._sort_matches()`, dashboard, stats, coach, reports and AI payload building order playable rows by `Match.played_at` without filtering on exact date truth.
- `match_date_truth()` can identify exact/non-exact rows, but broad metric flows do not yet enforce it.

## Steam History vs Demo Linkage Findings

Detected demo-to-placeholder links:

| demo row | linked steam_history row |
|---:|---:|
| 21 | 5 |
| 22 | 6 |
| 23 | 7 |
| 24 | 8 |
| 25 | 9 |
| 26 | 10 |
| 27 | 11 |
| 28 | 12 |
| 29 | 13 |
| 30 | 14 |
| 31 | 15 |
| 32 | 16 |
| 33 | 17 |
| 34 | 18 |
| 35 | 19 |
| 36 | 20 |
| 70 | 69 |

Rows `21-24` are the highest-value backfill candidates because their linked placeholders contain exact Steam GC metadata while the playable demo rows still use file-mtime fallback.

## Demo File / Share Code Findings

Rows with demo file/share-code linkage:

- `steam_history` rows `9-20, 69` have `demo_file` paths containing their share code.
- `demo` rows `25-36, 70` reference the same retained demo files and are exact.
- `demo` rows `21-24` have share codes in raw JSON but no `demo_file`; they still link to `steam_history` rows `5-8`.
- `demo` rows `37-38` have no share code and no demo file reference in DB.

No production files were opened for mutation, moved, deleted or cleaned.

## Whether Full Reset Is Recommended

No.

Full reset/resync is not justified:

- All playable rows are classifiable.
- The primary one-button import path is now accepted for controlled personal use.
- The problematic playable rows are a small bounded set: six approximate rows.
- Four approximate rows are recoverable from existing DB metadata.
- Two approximate rows can be safely left marked approximate/unknown.
- `steam_history` placeholders are excluded from metrics by current playable query logic.

Controlled reconciliation is safer than reset. Full reset would risk unnecessary live Steam/API work, parser reruns, storage growth and loss of useful retained parser/debug state.

Comparison:

- Controlled reconciliation: recommended.
- Full DB reset: not recommended.
- Re-sync Steam history only: useful later for bare placeholders, but not required before WP-015 metric gating.
- Re-parse retained demos: not required for date truth diagnosis; may be useful only for future parser metric correctness.
- Leave legacy rows marked unknown/approximate: acceptable for unrecoverable rows, provided metrics gate them.

## Recommended Repair Plan

1. Back up production DB and record SHA.
2. Implement a dry-run first-class reconciliation helper that reads rows and prints proposed mutations.
3. Backfill rows `21-24` from linked `steam_history` rows `5-8`:
   - matching rule: demo raw JSON contains exactly one CSGO share code; matching `steam_history.external_match_id` has `raw_json.steam_metadata.match_time` and `played_at_source=steam_gc_match_time`;
   - update `demo.Match.played_at` to parsed Steam GC time;
   - update demo `raw_json.played_at`, `played_at_source`, `steam_metadata`, `match_date_status`, `match_date_source`, `match_date_truth_note`;
   - update nested `raw_json.match` date truth fields if present.
4. Normalize rows `1-8, 59`:
   - matching rule: `source=steam_history`, raw JSON contains `steam_metadata.match_time` and `played_at_source=steam_gc_match_time`;
   - update raw JSON `match_date_status=exact_match_date_available`, `match_date_source=steam_gc_match_time`, `match_date_truth_note`;
   - do not make them playable.
5. Decide placeholder policy for rows `9-20, 69`:
   - either leave `Match.played_at` null and add explicit placeholder note;
   - or backfill `Match.played_at` only if all UI/reporting paths preserve `steam_history` as non-playable.
   - conservative recommendation: do not rely on placeholder `Match.played_at` for metrics.
6. Mark rows `37-38` as explicit approximate:
   - update raw JSON `match_date_status=approximate_match_date`, `match_date_source=file_modified_fallback`, truth note;
   - keep existing `Match.played_at` only as approximate display/sort fallback, not exact metric time.
7. Add/adjust metric gating before WP-015 metric acceptance:
   - date-sensitive metrics must use exact-date rows only or explicitly degrade confidence.

Every DB repair step needs a backup and rollback plan. No repair was performed in this WP.

## Proposed WP-015A1 Backfill Scope

Minimal backfill scope:

- Exact backfill playable rows `21-24`.
- Normalize placeholder raw metadata for `1-8, 59`.
- Explicitly mark rows `37-38` approximate.
- Preserve all rows; delete nothing.
- Avoid live Steam/API and parser reruns for this minimal scope.

Optional later scope:

- Under explicit live authorization, re-query Steam GC metadata for bare share-code placeholders `39-58, 60-68`.
- Continue importing pending demos through the guarded one-button flow rather than bulk resync/reset.

Expected fields to update in a later repair:

- `matches.played_at` only for playable demo rows where exact Steam GC time is proven.
- `matches.raw_json.played_at`.
- `matches.raw_json.played_at_source`.
- `matches.raw_json.match_date_status`.
- `matches.raw_json.match_date_source`.
- `matches.raw_json.match_date_truth_note`.
- nested `matches.raw_json.match.*` date truth fields where present.

## Proposed Metric Gating Rules For WP-015

General:

- Treat `steam_gc_match_time + Match.played_at` as exact.
- Treat `file_modified_fallback`, missing status, unknown source and unavailable source as non-exact.
- Do not use approximate/unknown/legacy dates as exact chronological evidence.

Recent N matches:

- For strict recent-form metrics, use only playable rows with exact date truth.
- If non-exact playable rows are included for count-only aggregates, label the window degraded and avoid date claims.

Trend windows:

- Current/previous windows must use exact-date rows only.
- If fewer than the configured minimum exact rows exist, return insufficient-confidence instead of a trend.

Map stats:

- All-time map aggregates may include playable non-exact rows if the metric itself is valid, but UI must not imply the date window is exact.
- Date-filtered map stats must require exact dates.

Player form:

- Form score and recent deltas should use exact chronological ordering only.
- Approximate rows may be shown separately as parser/debug evidence, not as recency evidence.

Recommendation freshness:

- Recommendation start/end and evaluation freshness should compare against exact-date playable rows only.
- If a match has unknown/approximate date, it may be evaluated by explicit id/order only, not by date freshness.

Sorting/filtering UI:

- Default match list can display approximate rows, but should label date truth.
- Date filters should either exclude non-exact rows or include them only under an explicit "include approximate/unknown dates" option.
- Sorting should not silently mix file-mtime fallback with exact Steam match dates as if equivalent.

## Read-Only Commands Used

Preflight/read-only:

```bash
git status --short
git log --oneline -12
df -h
du -sh data/uploads data/tmp 2>/dev/null || true
sha256sum data/cs2_coach.db
systemctl status jc-coach --no-pager
python3 scripts/project_gate.py preflight
python3 scripts/project_gate.py changed
python3 scripts/project_gate.py required-checks
```

DB inventory used Python `sqlite3` in read-only URI mode:

```python
conn = sqlite3.connect("file:data/cs2_coach.db?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "select id,source,external_match_id,played_at,created_at,updated_at,demo_file,raw_json "
    "from matches order by id"
).fetchall()
```

Classification extracted:

- `raw_json.match_date_status`;
- `raw_json.match_date_source`;
- `raw_json.played_at_source`;
- nested `raw_json.match.*`;
- `raw_json.steam_metadata.*`;
- share codes from `external_match_id`, `demo_file` and raw JSON.

## Production DB Touched

No.

## Production Files Touched

No. Demo files were not opened for mutation, deleted, moved, cleaned or parsed.

## Live Import / Parser Run

No.

## Can Proceed To Repair

Yes.

Proceed to a separate explicit WP-015A1 repair only after backup/SHA evidence and a dry-run proposal. The minimal repair should be controlled DB metadata reconciliation, not reset/resync.
