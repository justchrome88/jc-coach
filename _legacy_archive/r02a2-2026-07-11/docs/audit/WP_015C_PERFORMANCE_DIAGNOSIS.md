# WP-015C-PERF Runtime Metrics Page Performance Diagnosis

Date: 2026-07-04

## RESULT: DIAGNOSED

WP-015C introduced a blocker-level runtime performance regression in metrics pages. The issue is CPU-bound repeated JSON parsing of large `matches.raw_json` payloads inside the new metric confidence/date-window helper path, not DB query volume, disk pressure, live jobs or parser/import activity.

## Baseline

- Git status before diagnosis: WP-015C code/docs/test changes present; no new code changes made in this diagnosis.
- DB SHA: `8811b08c3e15348ab60ee022887c90ecbe4a17b4bef8ea5d035c083d8f2b6f1c`
- Root disk: `38G` total, `18G` available, `51%` used.
- `data/uploads`: `3.6G`
- `data/tmp`: `4.0K`
- Service: `jc-coach.service` active, main PID `135152`.
- Service memory at baseline: about `276876 KiB RSS`.
- Host memory: `3.3GiB` total, `2.3GiB` available, `536MiB` swap used.

Unauthenticated local HTTP timing was not useful for page performance because the protected pages correctly returned `303` to `/login`:

- `/dashboard`: `303`, `0.001826s`
- `/stats`: `303`, `0.001084s`
- `/coach`: `303`, `0.001848s`
- `/matches`: `303`, `0.001090s`
- `/settings/imports`: `303`, `0.001248s`

No authenticated browser session was available to reuse safely. The diagnosis therefore measured the read-only service/page builders directly against the production DB.

## Data Size Observed

- Total `matches`: `70`
- Playable matches: `19`
- Exact playable date rows: `17`
- Approximate/excluded playable date rows: `2`
- Artifact rows:
  - `demo_parse_artifacts`: `19`
  - `demo_rounds`: `406`
  - `demo_player_rounds`: `4083`
  - `demo_weapon_stats`: `4744`
  - `demo_damage_events`: `11992`
  - `demo_duels`: `2848`
  - `demo_grenade_events`: `3445`

Playable `matches.raw_json` payloads are large:

- Total playable raw JSON bytes: `17,159,358`
- Average playable raw JSON bytes: about `903,124`
- Largest row: match `35`, about `1,289,150` bytes
- Typical large rows: about `0.8-1.2 MB` each

## Measured Page/Function Timings

Measurements were done with a read-only Python profiler script using SQLAlchemy query counting. Route template rendering was not included, so real browser page times may be higher.

| Function/route builder | Elapsed ms | Matches processed | Artifact rows touched | SQL queries | Classification |
|---|---:|---:|---:|---:|---|
| `load_playable_matches` | `88.50` | `19` | `0` | `1` | acceptable |
| `metric_confidence_helpers` loop, 20 iterations | `58459.85` | `19 x 20` | `0` | `0` | blocker |
| Approx single `get_summary(..., date_windowed=True)` from cProfile | `2996` | `19` | `0` | `0` | blocker |
| `dashboard_builder` | `11957.24` | `19` | `0` | `8` | blocker |
| `stats_builder_last30` | `10868.60` | `17` | `0` | `0` | blocker |
| `coach_builder` | `10315.68` | `19` | `11443` overview rows | `22` | blocker |
| `_demo_parse_overview()` only | `140.67` | `19` | `11443` overview rows | `5` | warning, not primary |
| `matches_builder_default` | `138.30` | `19` | `0` | `5` | acceptable |
| `settings_imports_builder` | `70.94` | import state | `0` | `7` | acceptable |
| `ai_payload_builder_read_only` | `15625.46` | recent exact matches | `0` | `7` | blocker if called synchronously |

Memory notes:

- `load_playable_matches` raised profiler process max RSS from about `66.1 MB` to `99.7 MB`, consistent with loading large raw JSON text columns.
- `coach_builder` raised profiler process max RSS from about `103.7 MB` to `153.1 MB`, largely from loading artifact overview ORM rows.
- Service RSS after diagnosis remained about `276876 KiB`; no runaway service memory was observed.

## DB Query Findings

The slow pages are not primarily query-count bound:

- `stats_builder_last30` took about `10.9s` with `0` SQL queries after matches were already loaded.
- `metric_confidence_helpers` took about `58.5s` over 20 iterations with `0` SQL queries.
- `dashboard_builder` used only `8` SQL queries.
- `coach_builder` used `22` SQL queries, several repeated around recommendation progress, but the largest regression is still CPU JSON parsing.

Repeated DB reads still deserve cleanup:

- Dashboard calls `get_active_recommendation_progress()`, `get_all_recommendation_progress()` and `get_evaluations_by_match_id()` separately, which repeats recommendation/evaluation SELECTs.
- Coach repeats the same recommendation/evaluation work and also calls `recommendation_category_summary()`, which calls `get_all_recommendation_progress()` internally.
- These repeated queries are secondary compared with JSON parsing, but they add avoidable latency.

## cProfile Hot Path

Single `get_summary(matches, date_windowed=True)`:

```text
19009 function calls in 2.996 seconds
analytics.py:get_summary                     2.996s cumulative
metric_confidence.py:_raw                    2.766s cumulative, 627 calls
json.loads / json decoder                    2.743s cumulative, 627 calls
metric_confidence.py:metric_confidence_map   2.719s cumulative
metric_confidence.py:metric_confidence       2.718s cumulative, 11 calls
metric_confidence.py:exact_date_window_metadata 2.161s cumulative, 12 calls
```

Single `compare_periods(matches)`:

```text
19345 function calls in 2.949 seconds
analytics.py:compare_periods                 2.949s cumulative
analytics.py:get_summary                     2.672s cumulative, 2 calls
metric_confidence.py:_raw                    2.709s cumulative, 618 calls
json.loads / json decoder                    2.686s cumulative, 618 calls
```

`compare_periods()` also currently computes `current_summary = get_summary(current, date_windowed=True)` twice in sequence. This is a direct duplicated computation in `app/services/analytics.py`.

## Top Suspected Expensive Calls

Primary:

- `metric_confidence._raw(match)` reparses large `match.raw_json` every time it needs date truth or parser confidence.
- `metric_confidence_map()` calls `metric_confidence()` per metric.
- Each `metric_confidence()` recomputes `exact_date_window_metadata()`.
- `exact_date_window_metadata()` calls `is_exact_date_match()` and `is_approximate_date_match()`, each reparsing raw JSON.
- For 19 playable matches, a single summary can parse raw JSON more than 600 times.

Secondary:

- `compare_periods()` duplicates `current_summary`.
- Dashboard/stats/coach call `get_summary()`, `compare_periods()`, `get_dashboard_status()`, `get_aim_profile()`, `get_map_stats()` separately, each recomputing exact-date windows and confidence maps over the same match list.
- `/coach` `_demo_parse_overview()` loads all artifact rows from several tables into ORM objects. It took only about `141ms` now, but it touched `11443` artifact rows and grew memory; this will become a real issue as demos accumulate.
- Recommendation progress helpers repeat active recommendation/evaluation queries.

## Template/Payload Findings

Templates do not directly reference `raw_json`:

- `dashboard.html`: `0` raw_json references.
- `stats.html`: `0` raw_json references.
- `coach.html`: `0` raw_json references.

The payload issue is upstream: page contexts include ORM `Match` objects whose `raw_json` is loaded because the query selects full `Match` rows. Template rendering is not the measured primary bottleneck.

## Journal Findings

`journalctl -u jc-coach --since "30 minutes ago"` showed:

- no traceback;
- no HTTP 500;
- no accidental live Steam/import/parser jobs;
- no accidental report generation POST;
- only operator/browser GETs plus the local unauthenticated diagnostic GETs returning `303`.

Observed operator GETs after the WP-015C service restart included `/dashboard`, `/coach`, `/stats`, `/matches`, `/upload`, `/report`, `/settings/imports` and `/settings/storage`, all returning `200 OK`.

## Process Findings

No live Steam/demo/parser process was running.

Relevant process:

```text
/opt/jc-coach/.venv/bin/python /opt/jc-coach/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010
```

No running `ImportJob` rows were found.

## Acceptable / Warning / Blocker Classification

Acceptable:

- `/matches` data builder around `138ms`.
- `/settings/imports` data builder around `71ms`.
- Raw playable match load around `89ms`.

Warning:

- `/coach` artifact overview loads all artifact rows into ORM objects. Current isolated cost is about `141ms`, but it scales poorly.
- Recommendation progress/evaluation queries are repeated across page builders.

Blocker:

- Dashboard/stats/coach metric builders are around `10-12s` before template rendering.
- AI payload builder is around `15.6s` if called synchronously.
- Single `get_summary(..., date_windowed=True)` costs about `3s` over only 19 matches.

## Suspected Root Cause

Root cause is repeated parsing of large `matches.raw_json` strings in WP-015C metric confidence/date-window helper code. The app stores large parser payloads in `Match.raw_json`, and the helper does not cache parsed raw metadata per match/request.

The regression became visible because WP-015C added confidence/date-window metadata to many surfaces and those surfaces call the helper repeatedly.

## Whether WP-015C Can Be Committed As-Is

No.

Correctness intent is sound, but current runtime performance is blocker-level for the primary metrics pages. Committing as-is would bake in 10-15 second page builders on a tiny 19-match production dataset and will scale badly as more demos are imported.

## Whether WP-015D Runtime Metrics Acceptance Can Proceed

No.

WP-015D should wait for a minimal performance repair. Runtime acceptance would otherwise fail on page latency before validating correctness/visibility.

## Minimal Repair Proposal

Recommended minimal repair before WP-015D:

1. Cache parsed raw metadata per match per request/helper pass.
   - Parse `match.raw_json` once per match.
   - Pass a `MatchMetricContext` or `raw_by_match_id` map through exact-date and confidence helpers.
   - Avoid mutating ORM rows or production DB.

2. Compute date-window metadata once per match list.
   - `metric_confidence_map()` should compute the date window once and pass it into each metric confidence result.
   - Avoid recomputing `exact_date_window_metadata()` per metric.

3. Remove duplicated `current_summary` computation in `compare_periods()`.

4. Share page-level aggregate context.
   - Dashboard/stats/coach should compute sorted matches, exact matches, date window and metric confidence once per request.
   - Reuse those values across summary, comparison, dashboard status, aim profile and chart builders where practical.

5. Make recommendation progress reads less repetitive.
   - Load active recommendations/evaluations once per page where possible.
   - Keep recommendation planner scope unchanged.

6. Defer but track artifact overview optimization.
   - Replace full ORM row loads in `_demo_parse_overview()` with aggregate SQL counts and top weapon aggregate query.
   - Keep latest artifact as a small bounded query.

Acceptance target for the repair:

- Dashboard/stats/coach builder under `500ms` on the current production dataset, or at minimum under `1s` with clear evidence.
- Single `get_summary(..., date_windowed=True)` under `50ms` on current production data.
- No production DB mutation, no schema change, no live import/parser work.

## Production Safety

- Production DB touched: no mutation; read-only SELECT/profile queries only.
- Production files touched: no production demo/runtime files changed, deleted or moved.
- Live import/parser run: no.
- Schema changed: no.
- Commit made: no.

