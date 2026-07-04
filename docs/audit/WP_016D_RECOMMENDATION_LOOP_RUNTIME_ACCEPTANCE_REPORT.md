# WP-016D Recommendation Loop Runtime Acceptance Report

Date: 2026-07-04

## RESULT: PASS_WITH_WARNINGS

WP-016D accepted the runtime state after the controlled WP-016C survival recommendation refresh. The active survival recommendation is confidence-aware, read paths are non-mutating, the service restarts cleanly, and the loop is armed for the next eligible playable exact-date match.

Warning: the full next-match evaluation step was not exercised because there is no playable exact-date match with `id > start_after_match_id=70`. Per WP-016D safety rules, no production evaluation was forced or fabricated.

## DB SHA Before / After

Before:

```text
45bd8b7b4a513cfa509ab40137abdc72b54820da2fe1244d44c42b495b4e374e  data/cs2_coach.db
```

After:

```text
45bd8b7b4a513cfa509ab40137abdc72b54820da2fe1244d44c42b495b4e374e  data/cs2_coach.db
```

No production DB mutation was performed in WP-016D.

## Service Restart Result

`systemctl restart jc-coach` completed successfully.

Post-restart status:

```text
Active: active (running)
Main PID: 142544 (uvicorn)
Application startup complete.
Uvicorn running on http://127.0.0.1:8010
```

Journal showed clean shutdown/startup and GET redirects only. No startup traceback was observed.

## Active Recommendation Validation

Selected active recommendation:

```text
id=5
category=survival
status=active
started_at=2026-07-04 18:04:34.403854
ended_at=None
start_after_match_id=70
```

Recommendation `#5` validation:

- status: `active`;
- `needs_refresh=false`;
- `accepted_for_hard_progress=true`;
- baseline ids: `[23,24,25,26,27,28,29,30,31,32,33,34,35,36,70]`;
- baseline sources: all `demo`;
- baseline exact date truth: all `true`;
- baseline confidence date window: present;
- baseline confidence metrics: present;
- target metrics contain no `need data` placeholders.

Target metrics:

```text
{
  "kast": ">=63.54",
  "adr": ">=79.88",
  "entry_deaths_per_match": "<=1.3",
  "early_deaths_per_match": "warning: approximate metric, not used for hard scoring"
}
```

## Baseline Validation

Baseline ids:

```text
[23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 70]
```

All baseline rows are playable `source="demo"` rows and have exact match date truth. No `steam_history` baseline IDs are present.

Confidence checks:

- `baseline_metrics_json.confidence.date_window`: present;
- `baseline_metrics_json.confidence.metrics`: present;
- `health.baseline_non_playable_ids`: `[]`;
- `health.empty_required_metrics`: `[]`;
- `health.reasons`: `[]`.

## Health Validation

Active survival `#5`:

```text
needs_refresh=False
accepted_for_hard_progress=True
evaluations_checked=0
```

Active progress:

```text
recommendation_id=5
category=survival
completed_matches=0
progress_score=0
summary=Ждём новые матчи после постановки цели.
```

This is truthful: the recommendation is accepted/armed, but no post-refresh match has been evaluated yet.

## Old Legacy Recommendation Disposition

Old survival recommendation `#1`:

- status: `archived`;
- not selected as active;
- baseline ids remain legacy `steam_history` placeholders `6-20`;
- `needs_refresh=true`;
- `accepted_for_hard_progress=false`;
- 19 legacy gray evaluations preserved for audit/history.

Active `grenades` `#3` and active `map` `#4` remain legacy:

```text
(3, 'grenades', needs_refresh=True, accepted_for_hard_progress=False)
(4, 'map', needs_refresh=True, accepted_for_hard_progress=False)
```

They are not accepted for hard progress.

## UI / Read Helper Behavior

Safe read helpers were exercised:

- `get_active_recommendation_progress(db)`;
- `get_all_recommendation_progress(db)`;
- `recommendation_category_summary(db)`;
- `build_ai_coach_payload(db)`.

Results:

```text
ACTIVE_PROGRESS 5 survival False True 0 0 Ждём новые матчи после постановки цели.
ALL_PROGRESS [(3, 'grenades', True, False, 10), (4, 'map', True, False, 10), (5, 'survival', False, True, 0)]
CATEGORY_SUMMARY [('survival', 5, False, True, 0), ('aim', None, False, False, 0), ('grenades', 3, True, False, 10), ('map', 4, True, False, 10)]
AI_PAYLOAD_ACTIVE 5 False True
```

Authenticated browser session was not available to Codex. GET-only smoke was therefore performed without forging auth:

```text
/coach 303
/dashboard 303
/stats 303
/matches 303
/settings/imports 303
```

The `303` redirects are expected for unauthenticated requests. Authenticated UI observation remains an operator evidence gap.

## Read Mutation Safety

Counts before and after read helpers and AI payload build:

```text
COUNTS_BEFORE_AFTER (5, 75, 0) (5, 75, 0)
```

Meaning:

- `coach_recommendations`: unchanged at `5`;
- `match_recommendation_evaluations`: unchanged at `75`;
- `coach_reports`: unchanged at `0`.

No read helper created recommendations, evaluations or persistent reports.

## Evaluation Readiness

Checked for playable exact-date matches with `id > start_after_match_id=70`:

```text
ELIGIBLE_EXACT_MATCH_IDS_AFTER_70 []
```

No eligible post-refresh match exists.

Per WP-016D instructions:

- `evaluate_new_matches()` was not called on production;
- no evaluation was forced;
- no fixture or fake match was inserted;
- loop state is recorded as armed, not yet exercised.

## Full Next-Match Evaluation Exercised

No.

Reason: no playable exact-date match exists after active recommendation `#5.start_after_match_id=70`.

## Safety Checks

Import/job safety:

```text
import_jobs_total=19
import_jobs_running=0
```

Storage:

```text
3.6G data/uploads
4.0K data/tmp
28 .dem files
```

No new files were found under `data/uploads` or `data/tmp` after the WP-016D runtime check timestamp.

Process inspection showed only the running `uvicorn` service plus unrelated system Python processes. No Steam/import/parser/download process was running.

Journal checks found:

- no traceback;
- no HTTP 500;
- no `POST /settings/imports/pull-all`;
- no parser/import/download activity;
- no persistent report generation.

## Production Safety

- Production DB touched: no.
- Production files touched: no, except this audit report.
- Live import/parser run: no.
- Persistent report generated: no.
- Schema changed: no.
- DB reset/resync performed: no.
- Demo files deleted/moved: no.
- Commit made: no.

## Whether v0.8 Can Be Promoted Now

No.

The runtime state is safe and the recommendation loop is armed, but v0.8 should not be promoted until one real post-refresh playable exact-date match is imported or otherwise becomes available and the explicit/authorized evaluation path proves:

```text
recommendation #5 -> next match -> evaluation row with metric_confidence -> progress update
```

## Exact Blocker

No eligible post-refresh playable exact-date match exists:

```text
id > 70 exact playable matches: []
```

## Remaining Risks

- Full next-match evaluation/progress has not been exercised after refresh.
- Active `grenades` and `map` recommendations remain legacy and unaccepted for hard progress.
- Authenticated browser UI evidence was not captured by Codex due lack of authenticated session.
- Recommendation planner / verified top problem remains out of scope.
- Persistent report generation remains deferred because it mutates DB.
