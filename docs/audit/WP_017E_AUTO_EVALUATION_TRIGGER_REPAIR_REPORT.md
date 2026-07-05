# WP-017E Auto-Evaluation Trigger Repair Report

Date: 2026-07-05

## RESULT: REPAIRED

The Steam batch import path now defers parser-side recommendation evaluation until authoritative Steam date truth has been applied, committed and refreshed on the imported playable match. Exact-date gating remains unchanged: only playable matches with `match_date_status=exact_match_date_available` and `match_date_source=steam_gc_match_time` can create hard recommendation evaluations.

## Root Cause Confirmed

WP-017D root cause was confirmed in code:

- `demo_parser.import_demo_file(...)` evaluated the new match immediately after parser import.
- Steam exact date truth was applied later in `steam_demo_downloader._download_and_import_match(...)`.
- `evaluate_recommendations_for_match(...)` intentionally selects through exact-date playable matches, so the new Steam match was not eligible during the early parser-side call.
- Manual evaluation worked only after `_apply_primary_steam_date_truth(...)` had already made the row exact-date eligible.

## Files Changed

- `app/services/recommendation_tracking.py`
- `app/services/demo_parser.py`
- `app/services/steam_demo_downloader.py`
- `tests/test_steam_integration.py`
- `docs/audit/WP_017E_AUTO_EVALUATION_TRIGGER_REPAIR_REPORT.md`
- status/project docs updated for WP-017E outcome and next WP.

## Exact Repair Approach

- Added compact recommendation evaluation metadata helpers.
- Kept `import_demo_file(...)` non-Steam behavior intact by default.
- Added an explicit `evaluate_recommendations=False` path for Steam downloader imports, recording `deferred` metadata rather than silently returning no evaluation.
- In the Steam downloader, after import:
  - apply primary Steam date truth;
  - commit and refresh the imported match;
  - run `evaluate_recommendations_for_match(db, imported_match.id)` only after date truth is visible;
  - return and persist compact `recommendation_evaluations` plus status metadata in the demo download result.
- Non-exact Steam imports are marked `not_eligible` and are not hard-evaluated.
- Duplicate/repeated evaluation remains idempotent because the evaluator checks the unique recommendation/match pair before creating rows.

## Tests Added/Changed

- Added a Steam downloader test proving parser import is called with deferred evaluation and the recommendation evaluation is created only after exact Steam date truth is applied.
- Added assertions that:
  - `recommendation_evaluations` metadata is present in Steam downloader results;
  - batch-cap processing still exposes evaluation metadata for the one processed demo;
  - repeated targeted evaluation does not create duplicates;
  - legacy/needs-refresh recommendations are skipped;
  - non-exact Steam date imports are marked `not_eligible` and do not create evaluations.

## Test Results

```text
APP_ENV=test .venv/bin/pytest tests/test_recommendation_tracking.py -q
17 passed in 1.70s

APP_ENV=test .venv/bin/pytest tests -q
211 passed, 1 warning in 15.69s

.venv/bin/ruff check .
All checks passed!
```

The single warning is an existing Starlette/httpx deprecation warning from the test environment.

## DB SHA Unchanged

Expected: yes. WP-017E did not mutate production DB.

Observed before repair:

```text
3a96e5dc3d7f4cb850183731dc74c44a1a413f233d5d9fc0f76b7acbe02f927d  data/cs2_coach.db
```

Observed after repair:

```text
3a96e5dc3d7f4cb850183731dc74c44a1a413f233d5d9fc0f76b7acbe02f927d  data/cs2_coach.db
```

DB SHA unchanged: yes.

## Safety Declarations

| Item | Status |
|---|---|
| production DB touched | no |
| production runtime data files touched | no |
| repository code/docs touched | yes |
| live import/parser run | no |
| pending share code `#73` processed | no |
| schema changed | no |
| cap changed | no |
| raw demo files deleted/moved/compressed | no |
| manual evaluator on production DB | no |

## WP-017F Readiness

WP-017F Controlled Pending Share Code `#73` Import can start after this repair is accepted and the final gates remain green.

Constraints for WP-017F:

- keep `STEAM_IMPORT_MAX_DEMOS_PER_RUN=1`;
- process at most pending `#73` under explicit live authorization;
- require backup/SHA/storage/service/job/recommendation evidence;
- verify automatic evaluation metadata in parent result JSON;
- do not raise cap to `2` until one repaired-path live import is accepted.

## Remaining Risks

- The repair is covered by mocked/in-memory tests; it still needs one controlled live import to prove production-path metadata and evaluation creation against real Steam data.
- Parent `ImportJob.status` may still be coarse `failed` for `batch_cap_reached`; canonical outcome remains in `result_json`.
- Match mode remains unknown unless reliable Valve metadata is captured in a future WP.
- Raw demos are still retained by policy, so storage growth remains a controlled operational risk.
