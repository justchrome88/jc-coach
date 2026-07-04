# WP-016B Recommendation Legacy Refresh Repair Report

Date: 2026-07-04

## RESULT: REPAIRED

WP-016B implemented the minimal v0.8 recommendation-loop repair foundation: legacy/incompatible recommendations are detected, read surfaces label them as needing refresh, automatic evaluation skips legacy active recommendations, and the existing explicit category restart path creates confidence-aware active recommendations from playable exact-date baseline rows.

No production refresh was run in this WP.

## Files Changed

- `app/services/recommendation_tracking.py`
- `app/web/routes.py`
- `app/api/routes.py`
- `app/templates/coach.html`
- `app/templates/dashboard.html`
- `app/services/report_generator.py`
- `tests/test_recommendation_tracking.py`
- `tests/test_coach_first_ui.py`
- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_CONTROL.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/project_management/VERSION_ROADMAP.md`
- `docs/audit/WP_016B_RECOMMENDATION_LEGACY_REFRESH_REPAIR_REPORT.md`

## Legacy Detection Rules

Added read-only recommendation health helpers in `app/services/recommendation_tracking.py`:

- `recommendation_health(db, recommendation)`
- `recommendation_needs_refresh(db, recommendation)`
- `is_legacy_recommendation(db, recommendation)`

A recommendation is marked `needs_refresh` when any of these are true:

- `baseline_metrics_json` has no `confidence` block;
- `baseline_match_ids_json` contains non-playable rows such as `source="steam_history"`;
- baseline match IDs are missing or malformed;
- required baseline metrics for the category are empty;
- target metrics still say `need data`;
- stored evaluations lack `evidence_json.metric_confidence`;
- success/failure rules use weak/suppressed metrics as hard-looking evidence.

The health payload includes:

- `legacy`;
- `needs_refresh`;
- `accepted_for_hard_progress`;
- `reasons`;
- baseline source diagnostics;
- empty required metrics;
- weak-rule diagnostics;
- evaluation count checked.

## Coach / Progress Labeling Changes

Progress helpers now attach `health` metadata.

For legacy recommendations:

- `accepted_for_hard_progress=false`;
- displayed `progress_score` is clamped to `0`;
- raw score remains available as `raw_progress_score`;
- summary says refresh is required before accepting progress as coach evidence;
- existing evaluations remain visible as historical/unverified state.

UI changes:

- `/coach` shows a `needs_refresh` badge and warning for legacy current recommendations.
- `/dashboard` recommendation preview warns when the active recommendation is legacy.
- API and report/AI serialization now include the progress `health` block.

GET/read paths remain read-only.

## Explicit Refresh / Restart Path Implemented

The existing explicit category restart write path remains the intended controlled refresh path:

- web: `POST /coach/recommendations/category/{category}/restart`;
- API: `POST /api/recommendations/categories/{category}/restart`;
- service: `restart_recommendation_category(db, category)`.

Behavior:

- archives active/paused recommendations for the category;
- preserves old records for audit/history;
- creates a new active system recommendation;
- uses playable exact-date rows only;
- stores `baseline_metrics_json.confidence.date_window`;
- stores `baseline_metrics_json.confidence.metrics`;
- stores playable baseline IDs only;
- derives target metrics from actual baseline values.

The production refresh was not executed. WP-016C should run it only with explicit authorization, backup and DB SHA evidence.

## Automatic Evaluation Safety Changes

`evaluate_new_matches()` now skips active recommendations where `recommendation_needs_refresh(...)` is true.

This prevents future import/parser completion from creating new gray evaluations against the broken legacy production recommendations diagnosed in WP-016A.

Confidence-aware active recommendations still evaluate normally and preserve the unique recommendation/match evaluation behavior.

## Confidence-Aware Baseline Behavior

New/restarted recommendations use:

- `playable_match_select()`;
- exact-date recent rows via `exact_recent_matches()`;
- `exact_date_window_metadata()`;
- `metric_confidence_map()`;
- category-specific required metric checks.

Tests verify that restarted baseline IDs are playable exact-date rows and that baseline confidence metadata is present.

## Evaluation Confidence Behavior

New evaluations include `evidence_json.metric_confidence`.

The comparison helpers continue to use `is_metric_allowed_for_hard_claim(...)`, so suppressed/unavailable and weak warning-only metrics do not decide hard green/red outcomes. For example, `early_deaths` remains a warning/context metric for recommendation scoring.

## Tests Added / Changed

Added or updated tests for:

- legacy detection when baseline confidence is missing;
- legacy detection when baseline IDs point to `steam_history`;
- rule detection for weak hard-looking metrics;
- legacy progress labeling and score suppression;
- explicit restart creating confidence-aware playable exact-date baselines;
- `evaluate_new_matches()` skipping legacy active recommendations;
- new evaluation evidence containing `metric_confidence`;
- `/coach` displaying `needs_refresh` and historical/unverified labels;
- existing read/write split behavior.

## Test Results

Targeted checks:

```text
APP_ENV=test .venv/bin/pytest tests/test_recommendation_tracking.py tests/test_ai_coach.py tests/test_metric_truth.py -q
29 passed
```

Full suite:

```text
APP_ENV=test .venv/bin/pytest tests -q
206 passed, 1 warning
```

Lint:

```text
.venv/bin/ruff check .
All checks passed!
```

## DB SHA Before / After

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
- Production files touched: no, except documentation/report files.
- Live import/parser run: no.
- Production parser jobs run: no.
- Persistent reports generated: no.
- Production recommendations refreshed: no.
- Demo files deleted/moved: no.
- Schema changed: no.
- DB reset/resync performed: no.
- Commit made: no.

## Whether WP-016C Controlled Recommendation Refresh Can Start

Yes.

WP-016C should explicitly run the controlled production refresh for the selected category, most likely `survival`, with:

- production DB backup;
- DB SHA before/after;
- pre/post recommendation inventory;
- explicit single write action;
- verification that the old recommendation is archived and preserved;
- verification that the new active recommendation has playable exact-date baseline IDs and confidence metadata;
- verification that no live Steam/import/parser/report jobs were started.

## Remaining Risks

- Existing production recommendations `#1-#4` remain legacy until WP-016C explicitly refreshes them.
- The recommendation planner is still not a verified top-problem engine.
- Existing legacy evaluations remain historical/unverified and should not be used as accepted progress.
- Persistent report generation remains deferred because it mutates DB.
- Weak metrics remain weak; this WP prevents overclaiming but does not upgrade formulas.
