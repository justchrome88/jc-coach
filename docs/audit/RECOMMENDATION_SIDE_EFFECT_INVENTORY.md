# Recommendation Side Effect Inventory

Дата: 2026-07-03.

## Verdict

PASS_WITH_WARNINGS.

Stage 4 разделяет recommendation read/write behavior без schema changes. Read helpers and GET routes no longer create recommendations/evaluations or commit implicitly.

## Read Paths Reviewed

| Path/function | Before Stage 4 | After Stage 4 |
|---|---|---|
| `GET /api/recommendations/active` | Called `get_active_recommendation_progress()`, which called `ensure_default_recommendation()` and `evaluate_new_matches()` | Calls read-only progress helper; returns existing state or `404` |
| `GET /api/recommendations` | Could create defaults/evaluations through progress helper | Returns existing active recommendations only |
| `GET /api/recommendations/history` | Could create defaults through `list_recommendation_history()` | Lists existing history only |
| `GET /api/recommendations/categories` | Could create defaults/evaluations through summary helpers | Builds summary from existing rows only |
| `/dashboard` | Could create defaults/evaluations during page render | Reads existing recommendation/evaluation state only |
| `/coach` | Could create defaults/evaluations during page render | Reads existing recommendation/evaluation state only |
| Match list/detail evaluation widgets | Could create defaults/evaluations through evaluation helper | Reads existing evaluations only |
| AI/report read payloads using progress helpers | Progress helpers are now read-only | No implicit recommendation/evaluation writes from progress reads |

## Mutation Paths Reviewed

| Function/route | Mutation status |
|---|---|
| `ensure_default_recommendation()` / `ensure_default_recommendations()` | Explicit command/initialization path; may create system recommendations |
| `evaluate_new_matches()` | Explicit evaluation command; may create evaluations and ensure default recommendations |
| `evaluate_match()` | Command helper; adds an evaluation to the session |
| `POST /api/recommendations/{id}/status` | Explicit mutation path |
| `POST /api/recommendations/{id}/extend` | Explicit mutation path |
| `POST /api/recommendations/categories/{category}/restart` | Explicit mutation path |
| Web POST `/coach/recommendations/*` | Explicit mutation paths |
| CSV/JSON/DEM import flows | Explicit import mutation paths; still initialize/evaluate recommendations after imported matches |

## Service Functions Split

Read/query functions after Stage 4:

- `list_active_recommendations()`
- `get_active_recommendation()`
- `get_active_recommendation_progress()`
- `get_all_recommendation_progress()`
- `get_evaluations_by_match_id()`
- `get_all_evaluations_by_match_id()`
- `list_recommendation_history()`
- `recommendation_category_summary()`

Command/mutation functions:

- `ensure_default_recommendation()`
- `ensure_default_recommendations()`
- `evaluate_new_matches()`
- `evaluate_match()`
- `update_recommendation_status()`
- `extend_recommendation_target()`
- `restart_recommendation_category()`

## Fixed In Stage 4

- Removed implicit `ensure_default_recommendation()` from recommendation progress reads.
- Removed implicit `ensure_default_recommendations()` from history/category reads.
- Removed implicit `evaluate_new_matches()` from progress/evaluation reads.
- Added tests proving GET/read paths do not change recommendation/evaluation counts.
- Kept POST actions intentionally mutating.

## Remaining Later Work

- This is not recommendation planner.
- There is still no `ProblemSnapshot`.
- Import/parser flows still trigger explicit recommendation initialization/evaluation after writing matches.
- Existing multi-category defaults remain; future planner must replace broad defaults with one primary verified-problem recommendation.
