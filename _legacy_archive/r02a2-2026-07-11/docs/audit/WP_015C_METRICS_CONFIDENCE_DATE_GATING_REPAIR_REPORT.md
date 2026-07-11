# WP-015C Metrics Confidence and Date-Window Gating Repair Report

Date: 2026-07-04

## RESULT: REPAIRED

WP-015C implemented minimal v0.7 metric correctness guardrails without schema changes, live Steam work, parser jobs, production DB mutation, production demo cleanup or a recommendation planner rewrite.

The repair adds confidence metadata and exact-date window gating across dashboard, stats, coach, report, recommendation and AI payload paths. Approximate playable rows are no longer silently mixed into exact recent/trend/form windows.

## Files Changed

- `app/services/metric_confidence.py`
- `app/services/analytics.py`
- `app/services/aim_stats.py`
- `app/services/recommendation_tracking.py`
- `app/services/report_generator.py`
- `app/services/ai_coach.py`
- `app/web/routes.py`
- `app/templates/dashboard.html`
- `app/templates/stats.html`
- `app/templates/coach.html`
- `tests/test_analytics.py`
- `tests/test_ai_coach.py`
- `tests/test_recommendation_tracking.py`
- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_CONTROL.md`
- `docs/STEAM_IMPORT.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/project_management/VERSION_ROADMAP.md`
- `docs/audit/WP_015C_METRICS_CONFIDENCE_DATE_GATING_REPAIR_REPORT.md`

## Confidence Model Implemented

New helper: `app/services/metric_confidence.py`.

Implemented confidence levels:

- `exact`
- `partial`
- `low_confidence`
- `unavailable`

The helper combines:

- Metric Truth registry policy.
- Parser confidence metadata in `Match.raw_json` where present.
- Exact-date truth for date-windowed metrics.
- Sample size thresholds.
- Field coverage and known unsupported metrics.

Metrics that are suppressed or unsupported by current production data, including rating, grenade rating, aim rating, crosshair placement, traded deaths and side split hard claims, return `unavailable` or low confidence metadata instead of hard evidence.

## Date-Window Gating Implemented

Added exact-date helpers for recent/trend/form windows:

- playable rows only;
- exact-date rows only for exact windows;
- approximate rows counted as excluded;
- metadata returns `exact_date_matches`, `approximate_date_matches`, `excluded_from_exact_windows`, `confidence` and `insufficient_exact_sample`.

Applied gating to:

- dashboard recent/current/previous summary windows;
- stats date/last windows;
- `compare_periods()`;
- `calculate_form_score()`;
- ADR/aim recent period profiles;
- report period comparison;
- coach latest/recent evidence;
- recommendation baseline and latest ordering;
- AI coach recent matches and confidence payload.

Rows with `match_date_status=approximate_match_date` or `played_at_source=file_modified_fallback` are excluded from exact windows. `source="steam_history"` placeholders remain excluded from playable metric queries.

## Metrics Suppressed/Relabelled

The repair does not upgrade weak metrics. It relabels or suppresses unsupported facts:

- `rating`: unavailable when production coverage/field support is absent.
- `side_split`, `grenade_rating`, `aim_rating`, `crosshair_placement`, `traded_deaths`: unavailable unless real formulas/data exist.
- `KAST`, `swing_score`, `early_deaths`, utility and flash metrics: partial or low-confidence depending on Metric Truth policy, coverage and sample size.
- Map stats now expose sample-size confidence.
- Form score becomes unavailable/low when exact-date sample size is insufficient.

## UI/Payload Metadata Added

Dashboard and stats pages now show compact metric confidence summaries:

- exact-date row count;
- approximate/excluded row count;
- date-window confidence;
- key metric confidence labels.

Coach evidence cards expose confidence where available. Reports include date-window and metric confidence caveats. AI coach payloads include `confidence_metadata` and `metric_confidence`, and rules tell downstream AI consumers not to use unavailable or low-confidence metrics as hard claims.

## Recommendation Baseline/Evaluation Changes

Recommendation baselines now use exact-date recent rows and carry:

- date-window metadata;
- per-metric confidence metadata;
- sample counts.

Recommendation evaluation keeps unavailable/suppressed metrics out of hard success/failure evidence. Low-confidence metrics can remain secondary context.

## Tests Added/Changed

Updated tests cover:

- `steam_history` placeholders excluded from playable date windows;
- approximate-date demo rows excluded from exact recent/period windows;
- exact/approximate/excluded counts returned;
- form score unavailable when exact sample is insufficient;
- rating with zero coverage marked unavailable;
- KAST/swing/early-deaths caveated instead of exact hard claims;
- map stats sample-size confidence;
- recommendation baseline confidence metadata;
- AI payload excludes approximate rows from recent windows and reports unavailable metrics.

## Test Results

Final verification:

```text
APP_ENV=test .venv/bin/pytest tests/test_analytics.py tests/test_ai_coach.py tests/test_recommendation_tracking.py tests/test_metric_truth.py -q
34 passed in 1.73s

APP_ENV=test .venv/bin/pytest tests -q
199 passed, 1 warning in 13.58s

.venv/bin/ruff check .
All checks passed!

git diff --check
passed

python3 scripts/project_gate.py postflight
passed

sha256sum data/cs2_coach.db
8811b08c3e15348ab60ee022887c90ecbe4a17b4bef8ea5d035c083d8f2b6f1c  data/cs2_coach.db
```

## DB SHA Before/After

Before:

```text
8811b08c3e15348ab60ee022887c90ecbe4a17b4bef8ea5d035c083d8f2b6f1c  data/cs2_coach.db
```

After:

```text
8811b08c3e15348ab60ee022887c90ecbe4a17b4bef8ea5d035c083d8f2b6f1c  data/cs2_coach.db
```

## Production Safety

- Production DB touched: no.
- Production files touched: no production demo files were deleted, moved or cleaned.
- Live import/parser run: no.
- Schema changed: no.
- Full DB reset/resync performed: no.

## Remaining Risks

- WP-015C does not prove every metric formula with golden external fixtures.
- Weak metrics remain weak: KAST/trade, side splits, utility attribution and aim/grenade precision still need deeper parser validation before upgrading confidence.
- UI metadata is intentionally minimal; WP-015D must verify runtime visibility and wording on real pages.
- `ImportJob.status` remains coarse; import truth still lives primarily in `result_json`.
- Uploads/temp still live on root filesystem; dedicated storage remains recommended.

## Whether WP-015D Runtime Metrics Acceptance Can Start

Yes. WP-015D can start after final checks pass. It should be runtime/read-only acceptance of dashboard, stats, coach, reports and AI payload confidence behavior, not data cleanup or live import/parser work.
