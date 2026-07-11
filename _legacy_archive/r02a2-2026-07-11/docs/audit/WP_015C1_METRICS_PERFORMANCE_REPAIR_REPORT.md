# WP-015C1 Metrics Confidence Performance Repair Report

Date: 2026-07-04

## RESULT: REPAIRED

WP-015C1 repaired the blocker-level metrics page performance regression diagnosed by WP-015C-PERF. The repair keeps WP-015C confidence/date-window semantics intact while avoiding repeated parsing of large `matches.raw_json` payloads.

## Root Cause Confirmed

WP-015C-PERF found that the slow pages were CPU-bound, not DB-bound:

- production playable matches: `19`
- playable raw JSON total: about `17.2 MB`
- `get_summary(..., date_windowed=True)` before: about `2996 ms`
- dashboard builder before: about `11957 ms`
- stats builder before: about `10869 ms`
- coach builder before: about `10316 ms`
- AI payload builder before: about `15625 ms`

cProfile showed hundreds of `json.loads(match.raw_json)` calls per summary. A single summary parsed raw JSON `627` times over only 19 playable matches.

## Files Changed

- `app/services/metric_confidence.py`
- `app/services/analytics.py`
- `app/services/aim_stats.py`
- `app/services/recommendation_tracking.py`
- `app/services/report_generator.py`
- `app/services/ai_coach.py`
- `app/web/routes.py`
- `tests/test_analytics.py`
- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_CONTROL.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/project_management/VERSION_ROADMAP.md`
- `docs/audit/WP_015C1_METRICS_PERFORMANCE_REPAIR_REPORT.md`

## Caching/Context Design

Added `MetricContext` in `app/services/metric_confidence.py`.

The context provides:

- per-match raw JSON cache keyed by Python object identity;
- date-window metadata cache keyed by match object ids and requested sample size;
- helper construction through `metric_context(matches)`;
- `raw_match(match, context=...)` for services that need parser metadata.

Updated helpers:

- `is_exact_date_match(..., context=...)`
- `is_approximate_date_match(..., context=...)`
- `exact_date_matches(..., context=...)`
- `exact_recent_matches(..., context=...)`
- `exact_date_window_metadata(..., context=...)`
- `exact_period_windows(..., context=...)`
- `metric_confidence(..., context=..., date_window_metadata=...)`
- `metric_confidence_map(..., context=...)`

`metric_confidence_map()` now computes date-window metadata once per metric list instead of once per metric.

## Duplicate Computations Removed

- Reused one `MetricContext` per dashboard/stats/coach/AI/report builder pass.
- Reused cached exact-date/window metadata across summary, comparison, chart, aim and confidence helpers.
- Kept `compare_periods()` to one current summary and one previous summary.
- Avoided repeated raw JSON parsing in aim profile weapon breakdown, aim summary and coverage helpers.

The recommendation planner was not rewritten. Recommendation baseline/evidence paths only gained confidence-context reuse.

## Benchmark/Timing Before vs After

Measurements used the same read-only production DB service-level builder approach as WP-015C-PERF. Template rendering was not included.

| Builder/helper | Before | After | Result |
|---|---:|---:|---|
| `get_summary(..., date_windowed=True)` with shared context | ~`2996 ms` | `0.79 ms` after context raw cache is warm | repaired |
| `get_summary(..., date_windowed=True)` standalone no-context | ~`2996 ms` | `168.77 ms` | improved, still pays one 17 MB raw parse pass |
| metric confidence helper loop, 20 iterations | `58459.85 ms` | `180.01 ms` | repaired |
| dashboard builder | `11957.24 ms` | `164.07 ms` | repaired |
| stats builder, last 30 | `10868.60 ms` | `322.38 ms` | repaired |
| coach builder | `10315.68 ms` | `638.47 ms` | repaired under 1s; artifact overview remains the heaviest part |
| AI payload builder | `15625.46 ms` | `565.78 ms` | repaired |

The standalone no-context summary remains above the ideal `50-100 ms` target because it must parse about `17 MB` of raw JSON once. Runtime page builders now create a shared context and amortize that cost across all metric helpers. Further improvement would require moving small date/confidence metadata out of large raw parser payloads or adding a dedicated lightweight metadata projection, which is out of scope because schema changes are forbidden in this WP.

## Tests Added/Changed

Added `test_metric_context_caches_raw_json_parsing` in `tests/test_analytics.py`.

The test monkeypatches `app.services.metric_confidence.json.loads`, calls date-window metadata and confidence map repeatedly with the same context, and asserts raw JSON is parsed exactly once per match.

Existing WP-015C tests remain covered:

- approximate-date rows excluded from exact windows;
- exact/approx/excluded counts returned;
- rating unavailable when unsupported;
- KAST/swing/early deaths caveated;
- recommendation baseline confidence metadata;
- AI payload does not present unavailable metrics as hard facts.

## Test Results

Final verification:

```text
APP_ENV=test .venv/bin/pytest tests/test_analytics.py tests/test_ai_coach.py tests/test_recommendation_tracking.py tests/test_metric_truth.py -q
35 passed in 1.70s

APP_ENV=test .venv/bin/pytest tests -q
200 passed, 1 warning in 13.01s

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

- Production DB touched: no mutation; read-only timing queries only.
- Production files touched: no production demo files deleted, moved or cleaned.
- Live import/parser run: no.
- Schema changed: no.
- Recommendation planner rewrite: no.
- Parser rerun: no.
- Commit made: no.

## Whether WP-015C Can Now Be Committed

Yes, after final required checks pass. The correctness guardrails remain and the blocker-level runtime regression is repaired.

## Whether WP-015D Runtime Metrics Acceptance Can Start

Yes, after final required checks pass. WP-015D should still verify the actual authenticated runtime pages and UI confidence wording.

## Remaining Risks

- `/coach` still loads artifact overview ORM rows; current cost is acceptable, but this should be converted to aggregate SQL before the demo corpus grows much further.
- Standalone helper calls without a shared context still pay one raw JSON parse pass.
- Long-term fix for raw parser payload size likely needs a lightweight metadata projection or schema-backed metadata fields, which was out of scope here.
- Weak metrics remain weak; this repair changes performance only, not metric trust classification.
