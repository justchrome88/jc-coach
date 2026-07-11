# WP-016A Recommendation Loop Diagnosis

Date: 2026-07-04

## RESULT: DIAGNOSED

WP-016A diagnosed the current recommendation loop for the `v0.8` target in read-only mode. No code, tests, schema, production DB rows, live import, parser jobs, recommendation writes, persistent reports, or demo files were changed.

## Product Version Observed

`v0.7`

Evidence:

- `docs/CURRENT_STATUS.md`, `docs/HANDOFF.md`, `docs/PROJECT_CONTROL.md`, `docs/project_management/VERSION_ROADMAP.md` identify `v0.7` as current.
- `docs/audit/WP_015E_PROMOTE_METRICS_CORRECTNESS_TO_V0_7_REPORT.md` records `RESULT: PROMOTED`.
- Next planned target is `v0.8` / `WP-016 Recommendation Loop Acceptance`.

## DB SHA

```text
8811b08c3e15348ab60ee022887c90ecbe4a17b4bef8ea5d035c083d8f2b6f1c  data/cs2_coach.db
```

## Recommendation Model Inventory

Recommendation loop storage is in `app/db/models.py`:

- `coach_recommendations`
  - stores tracked recommendation lifecycle;
  - fields include `title`, `description`, `category`, `status`, `priority`, `started_at`, `ended_at`, `target_period_matches`, `baseline_period_matches`, `start_after_match_id`, `baseline_metrics_json`, `target_metrics_json`, `success_rules_json`, `failure_rules_json`, `baseline_match_ids_json`, `coach_comment`, `created_by`.
- `match_recommendation_evaluations`
  - stores one evaluation per recommendation/match;
  - unique key: `(recommendation_id, match_id)`;
  - fields include `score`, `status`, `evidence_json`, `positive_signals_json`, `negative_signals_json`, `coach_comment`.
- `coach_reports`
  - persistent rule/AI report table;
  - report generation is outside this diagnosis because persistent report generation mutates DB.

No schema change is required for diagnosis. The existing JSON fields can carry confidence metadata for new/rebuilt records.

## Production Recommendation State

Read-only DB inventory:

| Table | Rows |
|---|---:|
| `coach_recommendations` | 4 |
| `match_recommendation_evaluations` | 75 |
| `coach_reports` | 0 |

Recommendation statuses:

| Status | Count |
|---|---:|
| `active` | 3 |
| `completed` | 1 |

Evaluation statuses:

| Recommendation | Status | Count |
|---:|---|---:|
| 1 | `gray` | 19 |
| 2 | `gray` | 18 |
| 3 | `gray` | 19 |
| 4 | `gray` | 19 |

Current match inventory relevant to recommendation acceptance:

- playable demo rows: 19;
- `steam_history` placeholder rows: 51;
- playable exact-date rows: 17;
- playable approximate-date rows: 2.

No active Steam/import/parser process was observed. Process inspection showed only the running `uvicorn app.main:app` service plus unrelated system Python processes.

## Active Recommendation Findings

`get_active_recommendation()` chooses active `survival` first, so active recommendation is:

| Field | Value |
|---|---|
| id | 1 |
| category | `survival` |
| status | `active` |
| title | `Снизить первые смерти` |
| priority | `high` |
| created_by | `system` |
| created_at | `2026-07-01 19:22:57` |
| started_at | `2026-07-01 19:22:57.307791` |
| target_period_matches | 10 |
| baseline_period_matches | 15 |
| start_after_match_id | 20 |

Critical finding: active recommendation `#1` predates `v0.7` confidence and playable/date-window gating.

Its `baseline_match_ids_json` is:

```text
[6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
```

Those rows are currently `source="steam_history"` placeholders, not playable demo rows. They have Steam GC date metadata but no match performance metrics such as kills, ADR, KAST, entry deaths, or early deaths. As a result:

- `baseline_metrics_json` has no `confidence` block;
- target metrics are mostly `"need data"`;
- success/failure rules are legacy and still name `early_deaths` as a hard-looking success/failure metric;
- all 19 evaluations for recommendation `#1` are `gray`;
- all 19 evaluation `evidence_json` payloads lack `metric_confidence`.

Current active progress:

```text
recommendation_id=1
category=survival
completed_matches=10
target_matches=10
counts={"green": 0, "yellow": 0, "red": 0, "gray": 10}
progress_score=20
baseline_has_confidence=false
```

## Current Loop Flow

Creation:

- `app/services/recommendation_tracking.py`
  - `ensure_default_recommendation()`;
  - `ensure_default_recommendations()`;
  - `_new_system_recommendation()`.

Creation is still tied to import/parser write paths:

- `app/services/importer.py::import_rows()` calls `ensure_default_recommendation(db)` and `evaluate_new_matches(db)` after committing imported rows.
- `app/services/demo_parser.py::import_demo_file()` calls `ensure_default_recommendation(db)` and `evaluate_new_matches(db)` after storing a parsed match and artifacts.

Baseline:

- New recommendations now use `playable_match_select()`, exact-date sorting, `exact_recent_matches(..., 15)`, `exact_date_window_metadata()`, and `metric_confidence_map()`.
- Existing recommendations are not automatically migrated.

Evaluation:

- `evaluate_new_matches()` evaluates exact-date playable matches after `start_after_match_id`, excluding baseline and already evaluated IDs.
- `evaluate_match()` compares per-match evidence to stored baseline and writes `MatchRecommendationEvaluation`.
- Per-match evidence now includes `metric_truth_warnings` and `metric_confidence` for newly created evaluations.
- Existing production evaluations are legacy and lack those fields.

Progress:

- `get_active_recommendation_progress()` and `get_all_recommendation_progress()` are read helpers.
- Progress is calculated at read time from evaluation rows; it is not separately persisted.
- Read-path tests explicitly verify that recommendation read helpers and `/coach` GET do not commit or create rows.

Replacement/continuation:

- Manual write paths exist:
  - `update_recommendation_status()`;
  - `extend_recommendation_target()`;
  - `restart_recommendation_category()`.
- Web/API POST routes expose status, extend, and category restart actions.
- There is no accepted automatic policy for continue/replace once a target is completed.

## Baseline Calculation Findings

New/rebuilt baselines are compatible with `v0.7` guardrails:

- playable rows only;
- exact-date recent window;
- baseline match IDs stored;
- confidence metadata stored under `baseline_metrics_json["confidence"]`;
- metric confidence stored per registered metric;
- suppressed/unavailable metrics can be identified by Metric Truth.

Production active baseline is not compatible:

- active baseline `#1` was built before the confidence model;
- it points at `steam_history` placeholder rows;
- placeholder rows are non-playable and metrics-empty;
- baseline values are `None`, so target metrics are `"need data"`;
- no stored date-window metadata exists;
- no stored metric confidence exists.

This is the primary blocker for accepting the real production recommendation loop as-is.

## Evaluation Trigger Findings

Evaluation is automatic after import/parser writes, not on GET:

- CSV/JSON import path calls `evaluate_new_matches()`.
- Demo parser import path calls `evaluate_new_matches()`.
- `/coach`, `/dashboard`, and recommendation GET/API read paths use progress/list helpers and do not call `ensure_default_recommendation()` or `evaluate_new_matches()`.

The import/parser-triggered automatic evaluation is acceptable only if active recommendations are confidence-aware. With the current legacy active recommendation, future parser/import success would continue evaluating against a broken baseline unless the recommendation is explicitly refreshed/restarted first.

## Progress Update Findings

Progress is derived from `match_recommendation_evaluations`:

- completed count is capped to `target_period_matches`;
- status counts feed `progress_score`;
- current aggregate averages are computed from evaluation evidence;
- current aggregate confidence currently only says `{"evaluated_matches": N}`.

For active recommendation `#1`, progress is not meaningful for acceptance:

- first 10 target evaluations are all `gray`;
- evaluation evidence has no `metric_confidence`;
- baseline has no confidence and no real metric values;
- progress score `20` reflects gray placeholders more than real coach progress.

## Coach UI Findings

`app/templates/coach.html` displays:

- current tracked recommendation;
- explicit `not verified top problem` label;
- next match action;
- progress counts and score;
- success/failure rule summaries;
- evidence/confidence rows;
- Metric Truth warnings;
- latest match evaluation;
- AI validation status.

Good current behavior:

- GET `/coach` does not run AI, Steam, parser, import, or recommendation writes according to tests.
- The UI labels the current tracked recommendation as not a verified top problem.
- Weak Metric Truth notes are visible.
- AI/report actions are explicit POST actions.

Gap:

- If a baseline has no confidence block, the evidence rows silently have empty `confidence` objects.
- The UI does not clearly mark the active recommendation as legacy/unacceptable for hard progress claims.
- The visible recommendation can still look current even though its baseline points to non-playable placeholder rows.

## Metric Confidence Compatibility

Code compatibility for new/rebuilt records is mostly in place:

- `metric_confidence.py` provides cached `MetricContext`, exact-date matching, exact recent windows, and `metric_confidence_map()`.
- `recommendation_tracking._aggregate_baseline()` stores confidence metadata for new baselines.
- `recommendation_tracking._match_evidence()` stores metric confidence for new evaluations.
- `_compare_lower()`, `_compare_higher()`, and `_compare_adr()` use `is_metric_allowed_for_hard_claim()`.
- `ai_coach.build_ai_coach_payload()` serializes active/all recommendation progress and global confidence metadata.

Compatibility gap:

- Existing persisted baseline/evaluation JSON is not migrated.
- `early_deaths` is approximate and `usage_decision(..., "recommendation") == "warn"`, but existing success/failure rule text for recommendation `#1` still treats it as success/failure evidence.
- `survival` scoring logic now blocks approximate `early_deaths` as a hard claim in new evaluations, but old evaluation rows were generated before this metadata was stored.
- Legacy baseline IDs are `steam_history` placeholders, which should not be used as a playable baseline.

## Hard-Claim Risks

1. Active recommendation `#1` can be displayed as current progress even though the baseline is legacy, metrics-empty, and confidence-free.
2. Existing evaluations all lack `metric_confidence`, so they cannot be used as accepted `v0.7` evidence.
3. Legacy success/failure rule text for `survival` includes `early_deaths` as hard-looking success/failure language.
4. Existing baseline uses `steam_history` placeholder IDs, mixing non-playable rows into the recommendation history.
5. The completed `aim` recommendation `#2` also lacks baseline confidence and has only gray legacy evaluations.
6. Active `grenades` and `map` recommendations `#3/#4` have the same legacy baseline issue.
7. A future import/parser run would automatically evaluate against these legacy active recommendations unless repaired first.

## Legacy Recommendation Risk

Recommendation records `#1-#4` should be treated as legacy for `v0.8` acceptance:

- `#1 survival`: active; primary UI recommendation; incompatible baseline.
- `#2 aim`: completed; incompatible baseline/evaluations; should remain historical or be archived.
- `#3 grenades`: active; incompatible baseline.
- `#4 map`: active; incompatible baseline.

Recommended disposition for WP-016 repair:

- Preserve old records for audit/history.
- Do not silently mutate them on GET.
- Add or use an explicit write path to archive/restart or refresh a category with a confidence-aware baseline.
- Prefer creating a new accepted active recommendation over modifying legacy evidence in place, unless the repair explicitly documents a metadata migration.

## Minimal v0.8 Repair Scope

Keep WP-016 narrow:

1. Add an explicit recommendation refresh/restart acceptance path.
   - It must be a POST/write action or operator helper.
   - It must not run on GET.
   - It should archive/replace legacy active recommendation(s) or rebuild one target category with a confidence-aware baseline.

2. Add legacy-baseline detection.
   - Detect missing `baseline.confidence`.
   - Detect baseline IDs that point to non-playable rows.
   - Detect empty baseline metric values.
   - UI/API should label such recommendations as legacy/needs refresh and avoid hard progress claims.

3. Ensure accepted active recommendation has:
   - playable exact-date baseline rows only;
   - `baseline_metrics_json.confidence.date_window`;
   - `baseline_metrics_json.confidence.metrics`;
   - target metrics derived from actual baseline values;
   - success/failure rules that do not turn approximate/suppressed metrics into hard evidence.

4. Ensure evaluation path creates confidence-aware evidence.
   - New evaluations must include `metric_confidence`.
   - Suppressed/unavailable metrics must not decide green/red.
   - Low-confidence metrics may be notes only.

5. Add loop tests.
   - GET/read paths do not mutate.
   - Explicit refresh/restart creates confidence-aware active recommendation.
   - Legacy active recommendation is flagged.
   - Next exact-date playable match is evaluated once.
   - Progress updates from evaluation rows.
   - Approximate-date rows are excluded from baseline windows.
   - Weak metrics are caveated and not hard success/failure evidence.

Out of scope for minimal WP-016:

- full AI coach rewrite;
- new recommendation planner;
- parser/import changes;
- report generation rewrite;
- DB reset/resync;
- live Steam/API work.

## Proposed Acceptance Scenario

Recommended controlled scenario for WP-016 runtime acceptance:

1. Start from current production state with a DB backup.
2. Explicitly archive/restart one category, preferably `survival`, through a controlled write path.
3. Verify the new active recommendation:
   - has baseline IDs from playable exact-date rows;
   - has `baseline.confidence.date_window`;
   - has `baseline.confidence.metrics`;
   - has non-empty target metrics;
   - is labeled as current tracked recommendation, not verified top problem.
4. Evaluate a next match through a controlled local/test fixture or through the normal import/parser completion path only when explicitly authorized.
5. Verify one new `match_recommendation_evaluations` row:
   - no duplicate evaluation for the same recommendation/match;
   - `evidence_json.metric_confidence` present;
   - weak/suppressed metrics not used as hard green/red evidence.
6. Verify `/coach`:
   - shows next action;
   - shows progress update;
   - shows confidence/caveats;
   - GET does not mutate rows.
7. Verify no hidden import/parser/AI/report generation occurs during read-only page loads.

## Commands / Queries Used

Read-only commands included:

```bash
git status --short
git log --oneline -15
df -h
du -sh data/uploads data/tmp 2>/dev/null || true
sha256sum data/cs2_coach.db
systemctl status jc-coach --no-pager
python3 scripts/project_gate.py preflight
python3 scripts/project_gate.py changed
python3 scripts/project_gate.py required-checks
ps aux | grep -Ei 'uvicorn|steam|node|demo|parser|python' | grep -v grep
```

DB inspection was read-only through SQLAlchemy sessions using `select()` and aggregate counts only.

## Production Safety

- Production DB touched: no.
- Production files touched: no.
- Live import/parser run: no.
- New recommendations created: no.
- Active recommendation updated: no.
- Persistent reports generated: no.
- Demo files deleted/moved: no.
- Schema change needed: no for diagnosis; no schema change appears necessary for minimal repair.
- Commit made: no.

## Can Proceed To Repair

Yes.

Proceed to a focused WP-016 repair that explicitly refreshes or restarts a legacy recommendation into a confidence-aware active recommendation and proves recommendation -> next match -> evaluation -> progress without hidden GET mutations or weak-metric hard claims.
