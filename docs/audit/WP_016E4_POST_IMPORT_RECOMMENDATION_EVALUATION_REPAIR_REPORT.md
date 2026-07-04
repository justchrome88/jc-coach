# WP-016E4 Post-Import Recommendation Evaluation Repair Report

Date: 2026-07-04

## RESULT: REPAIRED_AND_EVALUATED

WP-016E4 repaired the missing post-import recommendation evaluation leg and then performed exactly one controlled production evaluation for existing playable exact-date match `#72` against active survival recommendation `#5`.

The repaired loop is now proven:

```text
recommendation #5 -> match #72 -> evaluation #76 with metric_confidence -> progress completed_matches=1
```

No live Steam/Valve import, demo download, parser job, schema change, persistent report generation, DB reset/resync, demo cleanup, AI rewrite or recommendation planner rewrite was performed in this WP.

## Root Cause

WP-016E3 successfully imported and parsed match `#72`, but the parser/import completion path depended on a broad `evaluate_new_matches(db)` sweep after parser artifact persistence. That call did not target or report the newly imported match, and import success was allowed to return without asserting that an eligible confidence-aware recommendation had been evaluated.

Read-only production checks before repair showed:

- recommendation `#5` was active, `survival`, `start_after_match_id=70`;
- recommendation `#5` had `needs_refresh=false` and `accepted_for_hard_progress=true`;
- match `#72` existed, `source=demo`, `map_name=de_dust2`, exact-date via `steam_gc_match_time`;
- match `#72` was included by `_ordered_matches(db)`;
- match `#72` was not in `#5.baseline_match_ids_json`;
- no evaluation existed for recommendation `#5` and match `#72`.

A disposable DB-copy probe confirmed the evaluation logic could evaluate `#72` when called directly. The defect was the post-import trigger contract: it was not target-specific and did not make a missed eligible evaluation visible.

## Files Changed

- `app/services/recommendation_tracking.py`
- `app/services/demo_parser.py`
- `tests/test_recommendation_tracking.py`
- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_CONTROL.md`
- `docs/project_management/VERSION_ROADMAP.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/audit/WP_016E4_POST_IMPORT_RECOMMENDATION_EVALUATION_REPAIR_REPORT.md`

## Repair Summary

Added targeted evaluation helper:

```text
evaluate_recommendations_for_match(db, match_id)
```

Behavior:

- selects only playable exact-date matches through the same `_ordered_matches(db)` path used by recommendation evaluation;
- skips legacy/needs-refresh recommendations;
- skips baseline match ids;
- respects `start_after_match_id`;
- skips existing recommendation/match evaluation rows;
- commits and refreshes created evaluations;
- preserves `evidence_json.metric_confidence`.

Updated `import_demo_file(...)` to call the targeted helper for the newly imported demo match after parser artifacts are saved. The import result now includes a compact `recommendation_evaluations` list so future missed evaluation cases are visible.

`evaluate_new_matches(db)` continues to work and now shares the same recommendation/match eligibility helper.

## Tests Added / Changed

Updated `tests/test_recommendation_tracking.py` to cover:

- eligible target match after `start_after_match_id` gets an evaluation;
- baseline ids are excluded;
- legacy/needs-refresh recommendations are skipped;
- duplicate evaluations are not created on repeated calls;
- new evaluation evidence includes `metric_confidence`;
- existing broad evaluation behavior still works.

## Test Results

Targeted pre-production checks:

```text
APP_ENV=test .venv/bin/pytest tests/test_recommendation_tracking.py tests/test_coach_first_ui.py tests/test_ai_coach.py tests/test_metric_truth.py -q
41 passed, 1 warning
```

Full suite:

```text
APP_ENV=test .venv/bin/pytest tests -q
210 passed, 1 warning
```

Lint:

```text
.venv/bin/ruff check .
All checks passed!
```

Pre-evaluation diff check:

```text
git diff --check
passed
```

## Backup Path

```text
data/manual_backups/cs2_coach_before_wp016e4_eval_match72_20260704_221816.db
```

Backup SHA:

```text
5d33469b7f4e5eff27354f04c635a8f6400a667b43858ed3716da4e0b6d0c696  data/manual_backups/cs2_coach_before_wp016e4_eval_match72_20260704_221816.db
```

## DB SHA Before / After Evaluation

Before controlled production evaluation:

```text
5d33469b7f4e5eff27354f04c635a8f6400a667b43858ed3716da4e0b6d0c696  data/cs2_coach.db
```

After controlled production evaluation:

```text
36ccd84dc5c695af1c75a74f8d1059ade68a2a0355bb43aca1a7b473dd68f320  data/cs2_coach.db
```

The DB changed because the authorized controlled evaluation created `match_recommendation_evaluations.id=76`.

## Exact Production Evaluation Action Performed

Exactly one controlled production evaluation operation was run:

```bash
.venv/bin/python - <<'PY'
import json
from app.db.session import SessionLocal
from app.services.recommendation_tracking import evaluate_recommendations_for_match

with SessionLocal() as db:
    evaluations = evaluate_recommendations_for_match(db, 72)
    print(json.dumps([
        {
            "id": evaluation.id,
            "recommendation_id": evaluation.recommendation_id,
            "match_id": evaluation.match_id,
            "status": evaluation.status,
            "score": evaluation.score,
            "coach_comment": evaluation.coach_comment,
        }
        for evaluation in evaluations
    ], ensure_ascii=False, default=str, indent=2))
PY
```

Output:

```json
[
  {
    "id": 76,
    "recommendation_id": 5,
    "match_id": 72,
    "status": "green",
    "score": 90,
    "coach_comment": "Хороший матч по survival: первых смертей меньше, impact не потерян."
  }
]
```

## Recommendation #5 Before / After

Before evaluation:

```text
evaluation_count=0
completed_matches=0
progress_score=0
summary=Ждём новые матчи после постановки цели.
needs_refresh=false
accepted_for_hard_progress=true
```

After evaluation:

```text
evaluation_count=1
completed_matches=1
progress_score=10
raw_progress_score=10
last_status=green
needs_refresh=false
accepted_for_hard_progress=true
summary=Цель пока проваливается: нужны изменения в следующих матчах.
```

The low progress score is expected after one completed match out of a 10-match target period.

## Match #72 Validation

```text
id=72
source=demo
map_name=de_dust2
played_at=2026-07-04 15:31:49
exact=true
match_date_status=exact_match_date_available
match_date_source=steam_gc_match_time
played_at_source=steam_gc_match_time
demo_file=/opt/jc-coach/data/uploads/20260704190858_5c1b0e8aac_CSGO-DearK-t4hWu-OUquu-aoKwy-KhMMB.dem
```

## Evaluation Row Validation

Exactly one evaluation exists for recommendation `#5` and match `#72`:

```text
id=76
recommendation_id=5
match_id=72
status=green
score=90
coach_comment=Хороший матч по survival: первых смертей меньше, impact не потерян.
```

Evidence:

```text
has_metric_confidence=true
metric_confidence_keys=["entry_deaths", "early_deaths", "kast", "adr", "utility_damage", "flash_assists", "result"]
entry_deaths=0
early_deaths=3
kast=61.11
adr=108.6
positive=["entry deaths ниже baseline", "ADR не ниже baseline"]
negative=[]
```

Weak metrics were caveated:

```text
metric_truth_warnings=[
  "early_deaths should be used with warning for recommendation: approximate reliability.",
  "kast should be used with warning for recommendation: approximate reliability.",
  "flash_assists should be used with warning for recommendation: approximate reliability."
]
```

No duplicate recommendation/match evaluations exist.

## Progress Update Validation

Progress moved from waiting to one completed match:

```text
completed_matches=1
last_status=green
progress_score=10
health.needs_refresh=false
health.accepted_for_hard_progress=true
```

## Legacy Recommendation Safety

Legacy recommendations received no new evaluation for match `#72`:

```text
#1 survival archived: match #72 evaluations=0
#3 grenades active legacy/needs_refresh: match #72 evaluations=0
#4 map active legacy/needs_refresh: match #72 evaluations=0
#5 survival active accepted: match #72 evaluations=1
```

No persistent report was generated.

## Import / Parser / Job Safety

- new import jobs during WP-016E4: no;
- running import jobs after evaluation: `0`;
- live Steam/Valve import: no;
- demo download: no;
- parser job: no.

## Storage / File Safety

Before and after controlled evaluation:

```text
3.8G data/uploads
4.0K data/tmp
29 .dem files
```

No production demo files were deleted or moved.

## Service / Log Safety

Service restart after the repair/evaluation succeeded:

```text
Active: active (running)
Application startup complete.
```

Unauthenticated smoke returned expected login redirects:

```text
/coach 303 -> /login
/dashboard 303 -> /login
/stats 303 -> /login
/matches 303 -> /login
/matches/72 303 -> /login
/settings/imports 303 -> /login
```

No authenticated session was available to Codex, and auth was not bypassed. Journal showed clean shutdown/startup and no traceback/500 evidence.

## Production Safety

- production DB touched: yes, controlled backup plus one evaluation row;
- production files touched: yes, backup DB and docs/report;
- production demo files deleted/moved: no;
- live import/parser run: no;
- persistent report generated: no;
- schema changed: no;
- DB reset/resync performed: no;
- AI coach rewrite/planner rewrite: no;
- commit made: no.

## Whether WP-016F Promote To v0.8 Can Start

Yes.

The primary survival recommendation loop has been repaired and proven for one real post-refresh playable exact-date match:

```text
recommendation #5 -> match #72 -> evaluation #76 with metric_confidence -> progress update
```

## Remaining Risks

- Legacy active `grenades #3` and `map #4` remain `needs_refresh` and are not accepted for hard progress.
- The progress score remains low after one match because the target period is 10 matches; this is expected and truthful.
- Authenticated browser UI was not directly inspected by Codex because no authenticated session was available.
- `data/uploads` and `data/tmp` remain on the root filesystem; storage guards remain required for future imports.
