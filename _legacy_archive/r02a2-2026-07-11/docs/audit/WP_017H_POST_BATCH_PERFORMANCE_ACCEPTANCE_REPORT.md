# WP-017H Post-Batch Performance Acceptance Report

Date: 2026-07-05

## RESULT: ACCEPTED_WITH_WARNINGS

Runtime and server-side read-only performance are accepted at the current post-WP-017 data volume: 76 total matches, 22 playable demo matches and 22 parser artifacts. The service stayed healthy, DB SHA stayed unchanged, read-only helper timings were under the 2s soft threshold, logs were clean, and no import/parser/evaluator jobs were created.

Warnings remain because Codex did not have an authenticated owner browser session for true UI timing, `/coach` still loads all parser overview rows, and cap/promotion remain governed by the next explicit WP.

## Product Version Observed

`v0.8`

Target remains `v0.9` Real Data Onboarding / Bulk Demo Usage.

## DB SHA Before/After

Before checks:

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

After checks:

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

DB SHA unchanged: yes.

## Service Health

`jc-coach.service` was active/running before and after the read-only probes.

| Field | Value |
|---|---|
| active state | `active` |
| substate | `running` |
| main PID | `146750` |
| active since | `Sat 2026-07-04 22:18:58 MSK` |
| uptime at start | about `5h45m` |
| temp env | `TMPDIR=/opt/jc-coach/data/tmp`, `TEMP=/opt/jc-coach/data/tmp`, `TMP=/opt/jc-coach/data/tmp` |

## Memory Snapshot

| Point | MemoryCurrent | MemoryPeak |
|---|---:|---:|
| before probes | `225,148,928` bytes | `253,173,760` bytes |
| after probes | `225,394,688` bytes | `253,173,760` bytes |

Memory stayed stable. No non-settling growth was observed.

## Authenticated UI Timing

Not fully accepted in this WP.

Codex did not have an authenticated owner browser/session cookie and did not bypass auth. Recent service logs show owner-browser `200 OK` GETs for `/coach`, `/matches`, `/report`, `/upload` and `/dashboard`, but those are operator/session evidence, not direct Codex timing evidence.

## Unauthenticated Redirect Evidence

Unauthenticated `curl` checks against the running service were used only as service-alive/auth-boundary evidence.

| Route | HTTP | Redirect | Time |
|---|---:|---|---:|
| `/dashboard` | `303` | `/login` | `0.001808s` |
| `/stats` | `303` | `/login` | `0.001701s` |
| `/coach` | `303` | `/login` | `0.001417s` |
| `/matches` | `303` | `/login` | `0.001278s` |
| `/matches/75` | `303` | `/login` | `0.001409s` |
| `/matches/76` | `303` | `/login` | `0.001241s` |
| `/settings/imports` | `303` | `/login` | `0.000982s` |

These timings do not prove authenticated page rendering performance.

## Read-Only Builder/Helper Timing

Existing read-only service/model helper sequences were timed against production DB using `.venv/bin/python`. Each timing ran five repetitions with a fresh session and rollback/close; no route POST, report generation, import, parser or evaluator path was called.

| Workload | Min | Avg | Max | Notes |
|---|---:|---:|---:|---|
| dashboard builder | `256.73ms` | `283.77ms` | `326.02ms` | 22 matches, 7 maps, 20 chart points, active recommendation `#5` |
| stats builder | `395.61ms` | `416.45ms` | `435.99ms` | selected 20 exact recent matches |
| coach builder | `598.73ms` | `652.27ms` | `741.78ms` | includes parser overview across all artifacts |
| matches list builder | `146.03ms` | `153.00ms` | `157.77ms` | 22 page items |
| match detail `#75` builder | `284.68ms` | `288.92ms` | `299.64ms` | 19 rounds, 138 duels, 214 grenade rows |
| match detail `#76` builder | `276.23ms` | `292.86ms` | `313.19ms` | 15 rounds, 105 duels, 134 grenade rows |
| import settings builder | `56.74ms` | `59.12ms` | `60.81ms` | 1 Steam account, 20 visible jobs |
| report page builder | `0.17ms` | `0.20ms` | `0.28ms` | no persistent report exists |

All measured read-only workloads were below the 2s soft accept threshold.

## DB/Data Snapshot

| Item | Value |
|---|---:|
| total matches | `76` |
| playable demo matches | `22` |
| demo parse artifacts | `22` |
| recommendation `#5` evaluations | `3` |
| recommendation `#5` progress | `3/10`, score `15` |
| queued/running `steam_import_all` | `0` |

Recommendation `#5` evaluations remained:

| Evaluation | Match | Status | Score |
|---:|---:|---|---:|
| `#76` | `#72` | `green` | `90` |
| `#77` | `#75` | `red` | `0` |
| `#78` | `#76` | `yellow` | `45` |

Historical queued non-parent Steam jobs still exist:

| Job | Type | Status |
|---:|---|---|
| `#1` | `steam_openid_linked` | `queued` |
| `#10` | `match_history_sync` | `queued` |

No queued/running parser-like or evaluator-like jobs were present.

## Page/Route Risk Findings

- `/coach` remains the heaviest read-only workload because parser overview loads all artifact, weapon, round, duel and grenade rows.
- At current volume this is acceptable: average measured server-side helper time was about `652ms`.
- The `/coach` parser overview touched `461` round rows, `3,228` duel rows, `4,033` grenade rows and `5,487` weapon profile rows.
- Optimization should be planned before relying on the same implementation at 50/100 demos, for example aggregate counts in SQL or defer heavy artifact overview data.
- Authenticated browser rendering/timing remains unmeasured by Codex and should be captured before claiming full owner UI performance.

## Log Safety

Journal scans during the WP-017H window found no traceback, exception, error or HTTP 500 lines.

## Import/Parser/Evaluator Safety

| Item | Status |
|---|---|
| live Steam/Valve import run | no |
| demo download run | no |
| parser job run | no |
| manual evaluator run | no |
| persistent app report generated | no |
| queued/running `steam_import_all` created | no |
| queued/running parser/evaluator job created | no |

## Storage Safety

| Item | Value |
|---|---:|
| root available at baseline | `17,686,470,656` bytes |
| `/tmp` available at baseline | `1,400,332,288` bytes |
| `data/uploads` | `4,461,189,306` bytes |
| `data/tmp` | `0` bytes |
| `data/manual_backups` | `1,426,202,624` bytes |
| demo files | `31` |

No production demo file was deleted, moved, compressed or created.

## Performance Acceptance Decision

`ACCEPTED_WITH_WARNINGS`

Accepted:

- service active/running;
- memory stable;
- no recent traceback/error/HTTP 500 evidence;
- DB SHA unchanged;
- read-only builder/helper timings under 2s;
- current `/coach` artifact overview acceptable at 22 demos;
- no import/parser/evaluator/report-generation side effects.

Warnings:

- authenticated owner browser timing was unavailable to Codex;
- `/coach` artifact overview is still all-row loading and should be optimized before materially larger demo volume;
- two historical queued non-parent Steam jobs remain from before WP-017;
- raw demos/backups are still on root-backed storage;
- cap remains `1`.

## Warnings Carried Forward

- Authenticated UI performance is not fully accepted from Codex-owned browser evidence.
- `/coach` parser overview should be revisited before 50/100 demos.
- Targeted pending-demo path still lacks parent `steam_import_all` metadata from WP-017F.
- Historical queued non-parent jobs `#1/#10` remain.
- Match mode remains provenance-only/unknown for Premier/Competitive/Wingman.
- Raw demos and backups remain on root-backed storage.
- 15 historical retained demo files remain unreferenced by current match/artifact paths.

## Whether Cap Can Be Raised Now

No.

The current cap remains `1`. Raising it should be a separate explicit WP after v0.9 promotion or a dedicated cap-change gate.

## Whether v0.9 Can Be Promoted Now

No.

WP-017H accepts performance with warnings, but it is not the promotion WP. The next recommended WP should make the explicit promotion/block decision and carry the warnings forward.

## Next Recommended WP

`WP-017I Promote Real Data Onboarding To v0.9`.

## Safety Declarations

| Item | Status |
|---|---|
| production DB touched | no logical mutation; read-only SELECT/GET checks only |
| production files touched | no runtime data mutation; repository docs/report updated |
| live import/parser run | no |
| manual evaluator run | no |
| persistent report generated | no |
| schema changed | no |
| cap changed | no |
| commit made | no |
