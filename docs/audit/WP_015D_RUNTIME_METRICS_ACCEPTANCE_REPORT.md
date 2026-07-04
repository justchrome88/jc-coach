# WP-015D Runtime Metrics Acceptance Report

Date: 2026-07-04

## RESULT: PASS_WITH_WARNINGS

WP-015D runtime metrics acceptance passed the read-only safety, restart, service health, confidence behavior and performance checks available from the server side. The main warning is evidence scope: after the explicit service restart in this WP, no reusable authenticated browser session/cookie was available to Codex, and no post-restart operator authenticated GETs arrived during the monitoring window. Therefore direct authenticated browser page timings were not captured. Server-side route-builder timings and pre-restart authenticated `200 OK` journal evidence support acceptance, but WP-015D should carry this evidence limitation forward.

## DB SHA Before/After

Before:

```text
8811b08c3e15348ab60ee022887c90ecbe4a17b4bef8ea5d035c083d8f2b6f1c  data/cs2_coach.db
```

After:

```text
8811b08c3e15348ab60ee022887c90ecbe4a17b4bef8ea5d035c083d8f2b6f1c  data/cs2_coach.db
```

The production DB SHA did not change.

## Service Restart Result

Explicit restart command:

```bash
systemctl restart jc-coach
```

Runtime start:

```text
2026-07-04 20:38:35 MSK
```

Post-restart service state:

- `jc-coach.service`: active/running
- main PID: `137738`
- startup traceback: none observed
- startup journal: `Application startup complete`, `Uvicorn running on http://127.0.0.1:8010`

## Pages Checked

Protected pages correctly redirect without an authenticated cookie:

```text
/dashboard status=303 total=0.005496s redirect=http://127.0.0.1:8010/login
/stats status=303 total=0.001194s redirect=http://127.0.0.1:8010/login
/coach status=303 total=0.001015s redirect=http://127.0.0.1:8010/login
/matches status=303 total=0.000958s redirect=http://127.0.0.1:8010/login
/settings/imports status=303 total=0.001060s redirect=http://127.0.0.1:8010/login
```

Authenticated browser evidence available before the explicit WP-015D restart, on the same committed code and service process started at `20:36:16 MSK`, showed `200 OK` for:

- `/dashboard`
- `/stats`
- `/coach`
- `/matches`
- `/upload`
- `/settings/imports`
- `/settings/storage`

After the explicit restart, no authenticated browser GETs were observed during the monitoring window, so post-restart authenticated browser timing remains a warning.

## Measured Page Timings

Direct authenticated curl timing was not possible without the owner password or a reusable browser session cookie. Codex did not forge a session.

Read-only service-level builder timings against production DB:

| Page/builder | Timing | Acceptance |
|---|---:|---|
| dashboard builder | `166.85 ms` | pass, under `1s` |
| stats builder | `311.96 ms` | pass, under `1s` |
| coach builder | `580.58 ms` | pass, under `2s` |
| settings/imports builder | `89.19 ms` | pass |
| AI payload builder, read-only | `506.35 ms` | pass/supporting |

No measured builder exceeded `1s`; no page-equivalent path exceeded the `5s` hard ceiling.

## Performance Acceptance Result

Accepted with warning.

The WP-015C1 performance repair remains effective at the service level. The unresolved warning is lack of direct post-restart authenticated browser timing from Codex.

## Confidence UI Observed

Static template/runtime data inspection confirms the UI exposes confidence/date-window metadata:

- `dashboard.html` includes `Metric confidence`, date-window confidence and key metric confidence labels for KAST, Rating and Swing.
- `stats.html` includes `Metric confidence`, date-window confidence and map sample confidence.
- `coach.html` includes evidence confidence, baseline date-window display when present, and weak metric notes.
- `matches.html` labels date truth as exact, approximate or unknown.

Runtime data feeding those templates:

```text
dashboard date_window:
total_playable_matches=19
exact_date_matches=17
approximate_date_matches=2
unknown_date_matches=0
excluded_from_exact_windows=2
confidence=exact
warnings=["2 non-exact matches excluded from exact date windows."]
```

## Date-Window Gating Observed

Observed:

- Dashboard full sample sees 19 playable rows, with 17 exact and 2 approximate/excluded rows.
- Stats `last` selection uses exact recent rows and reported 17 exact, 0 approximate, 0 excluded in the selected exact window.
- Approximate rows are not silently mixed into exact recent/trend/form windows.

## Unsupported Metrics Suppression Observed

Observed runtime confidence levels:

- `hltv_rating`: `unavailable`, present count `0`, coverage `0.0%`.
- `kast`: `low_confidence`.
- `swing_score`: `low_confidence`.
- `early_deaths`: `low_confidence`.
- `grenade_rating`: `unavailable`.
- `traded_deaths`: `unavailable`.
- `crosshair_placement`: `unavailable`.

Map stats expose sample-size confidence, for example:

```text
de_dust2: 5 matches, partial
de_inferno: 1 match, unavailable
de_overpass: 3 matches, low_confidence
de_ancient: 4 matches, low_confidence
de_mirage: 1 match, unavailable
```

## Coach/AI/Report Confidence Behavior

AI payload was inspected through the safe read-only builder path. It includes:

- `metric_confidence.date_window`
- `metric_confidence.metrics`
- exact/approximate/excluded date-window metadata
- unavailable/low-confidence metric levels for unsupported metrics

The current persisted active recommendation baseline predates WP-015C and does not contain a stored `confidence` block:

```text
active_recommendation_id=1
baseline_has_confidence=False
baseline_keys=['adr', 'early_deaths_per_match', 'entry_deaths_per_match', 'flash_assists', 'kast', 'kd', 'matches_count', 'utility_damage', 'winrate']
```

This is a warning, not a DB repair in this WP. New or rebuilt recommendations include confidence metadata, but existing persisted recommendations need an explicit future operator-safe refresh/reset path if the UI must show baseline confidence for old rows.

Persistent report generation was not run because it mutates DB by creating a `coach_reports` row. Report-write acceptance is deferred.

## Logs/Errors

Journal since runtime start showed:

- no startup traceback;
- no HTTP `500`;
- no `POST /settings/imports/pull-all`;
- no parser/import/download activity;
- only local unauthenticated diagnostic GETs returning `303`.

The string `settings/imports` appears in logs only as a GET redirect from local unauthenticated curl, not as an import POST.

## Safety Verification

Before/after:

- `data/uploads`: `3.6G`
- `data/tmp`: `4.0K`
- `.dem` file count: `28`
- `import_jobs_total`: `19`
- running import jobs: `[]`
- latest import jobs unchanged: `[(21, 'match_history_sync', 'succeeded'), (20, 'steam_import_all', 'failed'), (19, 'match_history_sync', 'succeeded'), (18, 'steam_import_all', 'failed'), (17, 'steam_import_all', 'failed')]`

Process inspection showed only the running uvicorn app plus diagnostic read-only Python commands; no Steam/import/parser/download job was running.

## Production Impact

- Production DB touched: no mutation; read-only SELECTs only.
- Production files touched: no production demo files deleted, moved or cleaned.
- Live import/parser run: no.
- Schema changed: no.
- Code/tests changed: no.
- Commit made: no.

## Whether v0.7 Can Be Promoted

Yes, with warnings.

The Metric Correctness runtime guardrails are working at the server-data and template level, the WP-015C1 performance regression is repaired, service restart is clean, logs are clean, and safety counters are unchanged. Carry forward the warnings:

- Direct post-restart authenticated browser timings were not captured by Codex because no authenticated session was available.
- Existing persisted recommendation baseline `#1` lacks the new stored confidence block until explicitly rebuilt/refreshed in a future WP.
- Report generation acceptance is deferred because persistent report generation mutates DB.
- `/coach` artifact overview is currently performant but still loads many artifact ORM rows and should be optimized before the demo corpus grows substantially.

## Remaining Risks

- Weak metrics are still weak; WP-015D verifies labels/gating, not formula truth upgrades.
- Existing recommendation records created before WP-015C may not carry confidence metadata in stored baseline JSON.
- Dedicated browser timing evidence should be recorded by the operator during or after promotion if stricter runtime UX evidence is required.

