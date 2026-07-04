# WP-017A Real Data Onboarding / Bulk Demo Usage Diagnosis

Date: 2026-07-04

## RESULT: DIAGNOSED

WP-017A diagnosed readiness for onboarding more real Steam/Valve demos and defined a safe `v0.9` plan.

This was diagnosis-only. No runtime code, tests, schema, production DB data, live Steam/Valve import, demo download, parser job, persistent report, DB reset/resync or production demo file lifecycle action was changed or run.

## Product Version Observed

`v0.8`

Current accepted loop:

```text
recommendation #5 -> real match #72 de_dust2 -> evaluation #76 with metric_confidence -> progress completed_matches=1
```

## Initial Read-Only Snapshot

- `git status --short`: no output.
- Latest commit: `f9f4508 Promote recommendation loop to v0.8`.
- Root filesystem: `38G` total, `19G` used, `18G` available, `52%` used.
- `data/uploads`: `3.8G`.
- `data/tmp`: `4.0K`.
- `data/manual_backups`: `1.2G`.
- Upload demo file count: `29`.
- `jc-coach.service`: active/running, PID `146750`.
- systemd environment: `TMPDIR=/opt/jc-coach/data/tmp`, `TEMP=/opt/jc-coach/data/tmp`, `TMP=/opt/jc-coach/data/tmp`.
- `python3 scripts/project_gate.py preflight`: passed.
- `python3 scripts/project_gate.py changed`: no changed/untracked files at start; guardian `PM_ORCHESTRATOR`.
- `python3 scripts/project_gate.py required-checks`: `preflight`, `changed`, `required-checks`, `postflight`, `git diff --check`.

Direct shell note: `.venv/bin/python` without explicit temp env resolves `tempfile.gettempdir()` to `/tmp`; with `TMPDIR/TEMP/TMP=/opt/jc-coach/data/tmp` it resolves to the intended app temp dir. Future shell-driven service functions must keep the explicit temp environment unless run through systemd/authenticated app flow.

## DB SHA

```text
36ccd84dc5c695af1c75a74f8d1059ade68a2a0355bb43aca1a7b473dd68f320  data/cs2_coach.db
```

## Current Data Inventory

Match inventory:

| Item | Count |
|---|---:|
| total matches | 72 |
| playable non-`steam_history` matches | 20 |
| playable `demo` matches | 20 |
| `steam_history` placeholders | 52 |

Playable date truth:

| Date truth | Count |
|---|---:|
| exact playable dates | 18 |
| approximate playable dates | 2 |
| unknown playable dates | 0 |

Map distribution for playable demos:

| Map | Count |
|---|---:|
| `de_dust2` | 7 |
| `de_overpass` | 4 |
| `de_ancient` | 4 |
| `de_nuke` | 2 |
| `de_mirage` | 1 |
| `de_cache` | 1 |
| `de_inferno` | 1 |

Parser artifact coverage:

| Artifact table | Rows | Distinct matches |
|---|---:|---:|
| `demo_parse_artifacts` | 20 | 20 |
| `demo_rounds` | 427 | 20 |
| `demo_player_rounds` | 4,281 | 20 |
| `demo_weapon_stats` | 5,002 | 20 |
| `demo_damage_events` | 12,491 | 20 |
| `demo_duels` | 2,985 | 20 |
| `demo_grenade_events` | 3,685 | 20 |

All 20 playable demo matches have a `demo_parse_artifacts` row. Six playable demo rows do not currently have `matches.demo_file` populated (`#21-#24`, `#37`, `#38`), but parser artifacts exist for them.

Steam placeholder/download state:

| `steam_history.raw_json.status` | Count |
|---|---:|
| `demo_download_pending` | 37 |
| `demo_imported` | 14 |
| `demo_download_error` | 1 |

The `demo_download_pending` count includes older/stale history rows and rows marked by previous failures/old cursor walks. It should not be interpreted as 37 fresh demos ready for bulk download. Current import code scopes demo download to fresh share codes from the current sync and skips candidates at or before the latest exact imported Steam match time.

Current Steam account state:

- one linked Steam account exists;
- match auth code is present;
- saved cursor is the latest imported share code from match `#72`;
- last sync time is `2026-07-04 19:08:37`.

Recommendation/evaluation state:

| Recommendation | Category | Status | Health | Evaluations | Notes |
|---:|---|---|---|---:|---|
| `#1` | survival | archived | legacy | 19 gray | old baseline `steam_history` ids `6-20`; no metric confidence |
| `#2` | aim | completed | legacy | 18 gray | historical only |
| `#3` | grenades | active | `needs_refresh` | 19 gray | safely not accepted for hard progress |
| `#4` | map | active | `needs_refresh` | 19 gray | safely not accepted for hard progress |
| `#5` | survival | active | accepted | 1 green | baseline ids `23-36,70`, evaluation `#76` on match `#72` |

Latest import jobs:

| Job | Type | Status | Outcome |
|---:|---|---|---|
| `#26` | `match_history_sync` | succeeded | `SUCCESS_NEW_MATCH_IMPORTED` |
| `#25` | `steam_import_all` | succeeded | `success`, one demo imported |
| `#24` | `match_history_sync` | succeeded | `SUCCESS_NO_NEW_MATCHES` |
| `#23` | `steam_import_all` | succeeded | `no_new` |
| `#22` | `steam_import_all` | failed | `storage_preflight_failed` from shell `/tmp` |
| `#20` | `steam_import_all` | failed | non-clean `batch_cap_reached` with one successful import |

No queued/running import job was observed in the initial service status or DB inventory.

## Storage Inventory

Filesystem and directory state:

| Item | Value |
|---|---:|
| root total | 39,973,224,448 bytes / 37.23 GiB |
| root available | 18,325,835,776 bytes / 17.07 GiB |
| `data/uploads` | 4,062,565,189 bytes / 3.78 GiB |
| `data/tmp` | 0 bytes by `du -sb`; 4.0K by `du -sh` |
| `data/manual_backups` | 1,201,012,736 bytes / 1.12 GiB |
| production DB file | 72M |

Demo files under `data/uploads`:

| Item | Value |
|---|---:|
| `.dem` / `.dem.bz2` files | 29 |
| `.dem.bz2` files | 0 |
| total demo bytes | 4,062,565,188 |
| large real-ish demo files (`>=1 MiB`) | 16 |
| tiny files (`<1 MiB`) | 13 |
| average across all demo files | 140,088,455 bytes |
| average across large demo files | 253,910,319 bytes |
| p90 demo size | 271,123,862 bytes |
| max observed demo size | 400,393,739 bytes |

Largest demo files:

| Size bytes | Path |
|---:|---|
| 400,393,739 | `data/uploads/20260704142549_84e85746be_CSGO-HRwaS-hoKid-wqu7z-BFh3Y-jkiaB.dem` |
| 293,225,371 | `data/uploads/20260704142925_5cb0be1667_CSGO-CnPaS-Wcyuh-TFC57-Xzotd-CuybE.dem` |
| 284,903,721 | `data/uploads/20260704142648_a9a2ecfc42_CSGO-oQNTD-3obBf-TiUsP-Y9X2y-52DVF.dem` |
| 271,123,862 | `data/uploads/20260704143301_0e38b143b1_CSGO-r5JPP-hv9eO-Uubhz-WOTah-OFSiA.dem` |
| 265,563,694 | `data/uploads/20260704142445_f50a73ee8c_CSGO-cAQhC-XL4SM-wWoxt-NNdVO-anUaK.dem` |

Storage consistency findings:

- 28 DB rows have `demo_file`; all 28 references exist.
- Those 28 DB references point to 14 unique raw demo paths because each imported Steam demo is referenced by both the `steam_history` placeholder and the playable `demo` row.
- 15 upload files are not referenced by `matches.demo_file`: 13 tiny 7-byte legacy/test-looking `.dem` files plus 2 larger retained files from previous failed/duplicate paths.
- No production demo file was deleted or moved during this diagnosis.

## Import Guard Settings

Current settings from app config/environment:

| Setting | Value |
|---|---:|
| `STEAM_IMPORT_MAX_DEMOS_PER_RUN` | 1 |
| `STEAM_IMPORT_MAX_BYTES_PER_JOB` | 2,147,483,648 bytes / 2.00 GiB |
| `STEAM_IMPORT_MAX_SINGLE_DEMO_BYTES` | 629,145,600 bytes / 600 MiB |
| `STEAM_IMPORT_MIN_FREE_BYTES` | 8,589,934,592 bytes / 8.00 GiB |
| `STEAM_IMPORT_PRESERVE_FREE_BYTES` | 5,368,709,120 bytes / 5.00 GiB |
| `STEAM_IMPORT_UNKNOWN_DEMO_RESERVE_BYTES` | 1,610,612,736 bytes / 1.50 GiB |
| stale running parent timeout | 3,600 seconds |
| startup stale repair | disabled |

Safety behavior:

- Parent `steam_import_all` performs storage preflight before work.
- Downloader uses `min(requested_limit, max_demos_per_run)`.
- `max_demos_per_run=1` is therefore a hard one-demo cap for the primary path.
- The storage budget checks temp writes, decompression writes and upload copy writes.
- If pending remains after the cap, result payload includes `batch_cap_reached`; because `ImportJob.status` is coarse, parent jobs can be `failed` for non-clean terminal outcomes even when one demo imported successfully. Canonical truth is `result_json.overall_outcome/statuses`.
- Share-code collection is represented by child `match_history_sync` jobs; demo download/parser/import truth is represented in parent `steam_import_all.result_json.demo_download`.
- Duplicate share codes are skipped by the `source/external_match_id` unique key. Duplicate demo imports are skipped by `import_demo_file(...)` when a playable `demo` row with the same external id already exists.
- The primary path uses exact Steam GC `match_time` as the only exact Steam date and skips candidates not newer than the latest exact imported Steam match.

## Demo Capacity Estimate

Current root free space is `17.07 GiB`.

Effective capacity under current guards:

- Preflight fails before a job starts when free space is below `8.00 GiB`.
- Preserve-free checks prevent individual writes from crossing `5.00 GiB`.
- Because preflight `8.00 GiB` is stricter for starting future jobs, the practical current addable retained-demo budget before the next run would fail preflight is about `9.07 GiB`.
- A single job can consume at most `2.00 GiB` across downloaded archive, decompressed temp file and stored raw file.
- A single decompressed demo cannot exceed `600 MiB`.

Estimated additional demos before preflight reaches the 8 GiB floor:

| Assumption | Estimate |
|---|---:|
| current large-demo average, ~254 MB retained each | ~38 more demos |
| current p90 size, ~271 MB retained each | ~35 more demos |
| current max observed, ~400 MB retained each | ~24 more demos |

These estimates assume no new manual backups, reports, logs or other data growth. They also do not include transient temp/archive/decompression overhead inside an active job. The current one-demo cap is therefore appropriate for first v0.9 batches.

## Recommended Import Batch Strategy

Recommended initial strategy for `v0.9`:

1. Keep `STEAM_IMPORT_MAX_DEMOS_PER_RUN=1` for the first `3` controlled runs.
2. Before every run, record DB SHA, `df -h`, `du -sh data/uploads data/tmp data/manual_backups`, upload demo count and service status.
3. Run through the authenticated/systemd app path when possible. If an operator uses a direct shell service call, explicitly set `TMPDIR/TEMP/TMP=/opt/jc-coach/data/tmp`.
4. After each run, inspect parent and child import jobs, demo_download counters, service memory, logs, parser result, new match id/date truth, recommendation evaluation, disk growth and DB SHA.
5. Stop after `3` successful one-demo runs and run WP-017D data/performance acceptance before raising the cap.

Do not raise to `2` or `3` demos per run until all of these are true:

- root free remains at least `12 GiB` before the run;
- `data/tmp` is empty after previous runs;
- no parser failure in the last `3` runs;
- no `batch_cap_reached` ambiguity is left unexplained in the report;
- `/coach`, `/stats` and `/matches` remain usable under authenticated owner session;
- recommendation `#5` evaluation count increments once per new eligible exact playable match;
- legacy `#3/#4` still receive no new evaluations.

If raised, prefer `max_demos_per_run=2` first, not `3`. A `3` demo cap should wait until a dedicated post-batch performance check confirms UI and parser stability.

Backup cadence:

- Create a DB backup before the first import batch WP.
- For one-demo exploratory runs, record DB SHA before/after each run.
- Create another DB backup before raising `max_demos_per_run`.
- Do not keep creating unlimited manual backups without storage accounting; backups already occupy about `1.12 GiB`.

Disk stop conditions:

- Stop if root free is below `12 GiB` before a planned run.
- Hard stop if root free approaches `10 GiB`; do not start a new import unless storage/backups are reviewed.
- Hard stop if current guard reports `storage_preflight_failed`, `disk_budget_exceeded` or `demo_too_large`.
- Hard stop if `data/tmp` retains large files after a job.
- Do not delete/move raw demos or backups as part of WP-017B/C unless a separate retention/storage WP explicitly authorizes it.

Parser/runtime stop conditions:

- Stop on any parser failure until the failed match and retained raw demo are inspected.
- Stop on any service traceback, HTTP 500, hung restart or running import job older than the stale threshold.
- Stop if one demo import/parser run exceeds roughly `3` minutes without a known Valve/network reason.
- Stop if service memory materially grows across runs and does not return near baseline; use `systemctl status` and journal evidence.

Metric/recommendation review cadence:

- Inspect metrics and recommendation progress after every imported exact playable match.
- Run a deeper data/performance review after `3` new exact playable matches.
- Stop and run WP-017D when recommendation `#5.completed_matches` reaches `4` or `5`, before chasing the full `10/10` target.

## Match Mode Classification Findings

Goal: determine whether current playable demos are Premier, Competitive, Wingman, mixed or unknown.

Read-only inspected sources:

- `matches.mode`;
- `matches.raw_json`;
- nested `matches.raw_json.match`;
- `steam_history.raw_json`;
- `demo_parse_artifacts.payload_json`;
- parser header fields;
- Steam GC metadata under `steam_metadata.raw_gc_metadata.watchable_match_info`.

Findings:

- All 20 playable demo rows have `matches.mode='demo'`.
- All 20 playable raw payloads have nested `match.mode='demo'`.
- Parser header fields include generic server metadata such as `server_name`, `map_name`, `patch_version`, demo version fields and game directory.
- Steam GC metadata currently stores `match_id`, `match_time`, `share_code`, exact played_at source and `watchable_match_info` fields such as `server_ip`, `tv_port`, `tv_spectators` and decrypt key.
- No reliable stored field was found for Premier vs Competitive vs Wingman.
- Map name is not sufficient and was not used as classification evidence.

Current classification:

| Classification | Confidence | Count |
|---|---|---:|
| unknown | unknown | 20 |

Important nuance: WP-016E3 documents match `#72` as the expected real Competitive Dust2 match from operator context, but the current persisted data does not independently preserve a reliable Competitive/Premier/Wingman mode field. For product/runtime purposes, `#72` and all current playable demos should be labeled `mode=unknown` until mode metadata is recoverable or explicitly captured.

Possible repair direction:

- Check whether the Steam GC helper can return mode/type fields not currently persisted.
- Check whether additional demoparser header/server vars expose game mode, queue type or ruleset.
- If recoverable, add mode extraction and backfill in a future authorized repair WP.
- If not recoverable, UI and reports should explicitly label existing demos as `mode_unknown` rather than guessing.

## Recommendation Loop Impact

What happens after importing more matches:

- The Steam import path downloads and parses the new demo, then `import_demo_file(...)` creates a playable `demo` match.
- The parser/import completion path now calls `evaluate_recommendations_for_match(db, match.id)` for the newly imported match.
- Recommendation `#5` evaluates the match if it is playable exact-date, not in the baseline ids, `match.id > start_after_match_id=70`, and no duplicate recommendation/match evaluation exists.
- Exact-date matching requires `match_date_status=exact_match_date_available` and `match_date_source=steam_gc_match_time`.
- Approximate or date-unavailable demos will not be accepted into exact-date recommendation windows.

Legacy recommendation safety:

- `#1` is archived and is not selected as active.
- Active `#3` and `#4` remain legacy/`needs_refresh`.
- `evaluate_recommendations_for_match(...)` skips recommendations where `recommendation_needs_refresh(...)` is true, so `#3/#4` should remain safely ignored.

Current target period:

- `#5.target_period_matches=10`.
- The target is reasonable for `v0.9`, but initial onboarding should not try to fill all 10 in one push.
- Use `3` new exact playable matches as the first review point, then `5`, then decide whether to continue to `10`.

After each import batch, check:

- new playable match id;
- `source=demo`;
- map and played_at;
- exact date source is `steam_gc_match_time`;
- parser artifact row exists;
- import parent/child result_json is terminal and truthful;
- evaluation for `#5` exists exactly once;
- `evidence_json.metric_confidence` exists;
- no new evaluations for `#1/#3/#4`;
- `completed_matches` increments as expected;
- progress wording remains bounded and not overclaimed.

## Performance Risk

Current parser-derived row density per demo:

| Table | Current rows/demo |
|---|---:|
| `demo_rounds` | ~21 |
| `demo_player_rounds` | ~214 |
| `demo_weapon_stats` | ~250 |
| `demo_damage_events` | ~625 |
| `demo_duels` | ~149 |
| `demo_grenade_events` | ~184 |

Estimated artifact row counts:

| Demo count | Rounds | Player rounds | Weapon stats | Damage events | Duels | Grenades |
|---:|---:|---:|---:|---:|---:|---:|
| 50 | ~1,068 | ~10,703 | ~12,505 | ~31,228 | ~7,463 | ~9,213 |
| 100 | ~2,135 | ~21,405 | ~25,010 | ~62,455 | ~14,925 | ~18,425 |
| 200 | ~4,270 | ~42,810 | ~50,020 | ~124,910 | ~29,850 | ~36,850 |

Expected behavior:

- Dashboard/stats primarily operate on match rows and cached raw JSON contexts. They should remain acceptable at 50-100 demos if exact-window logic stays cached.
- `/coach` is the highest risk because `_demo_parse_overview(...)` currently loads all `DemoWeaponStat`, `DemoRound`, `DemoDuel` and `DemoGrenadeEvent` rows into memory to compute overview counts/top weapons.
- At 50 demos this is likely still tolerable; at 100 demos it needs measurement; at 200 demos it should be optimized before relying on it.
- SQLite is acceptable for v0.9 controlled personal use at 50-100 demos, but the all-row artifact overview is not a good long-term shape.

Recommended performance gates:

- For `v0.9`, require authenticated page checks for `/coach`, `/stats`, `/dashboard`, `/matches` after batches.
- Use a soft threshold of `<2s` server-side page build for `/coach`, `/stats` and dashboard at the first batch acceptance.
- Use a hard stop if `/coach` exceeds `5s`, returns 500, or materially increases service memory after page load.
- Optimize `_demo_parse_overview(...)` before targeting 100+ parsed demos or before raising import cap above `2`.

## v0.9 Acceptance Criteria

Minimum data target:

- At least `25` playable parsed demo matches total, meaning `5` additional successful playable demo imports from the current `20`, unless storage/runtime safety stops earlier.
- At least `23` exact-date playable matches total; exact-date coverage should stay at or above `90%` for playable demo rows.
- Parser artifact coverage remains `100%` for playable demo rows.

Import stability:

- Every authorized import batch has a parent `steam_import_all` job with terminal status and truthful `result_json.overall_outcome/statuses`.
- Child `match_history_sync` jobs have clear `sync_outcome`.
- No stale running import job remains.
- Duplicate/no-new/batch-cap outcomes are documented without overclaiming clean success.

Parser stability:

- No untriaged parser failure.
- Raw demo retention metadata exists for success/failure.
- `data/tmp` is empty or explained after each run.

Recommendation evaluation stability:

- Recommendation `#5` receives exactly one evaluation per new exact playable post-refresh match.
- Evaluation evidence includes `metric_confidence`.
- Legacy `#3/#4` receive no new evaluations until explicitly refreshed.
- Progress increments and remains bounded by the `10` match target.

UI/runtime performance:

- Authenticated `/coach`, `/stats`, `/dashboard` and `/matches` load without 500s after batch.
- Soft page build target: `<2s`.
- Hard failure threshold: `>5s`, 500, traceback or persistent memory growth.

Storage safety:

- Root free remains at least `12 GiB` before each controlled run.
- Hard stop before starting another run if root free falls below `10 GiB`.
- Guard settings stay at `max_demos_per_run=1` until WP-017D accepts the first batch.
- No raw demo deletion/move/compression unless a future explicit storage WP authorizes it.

Match mode visibility:

- UI/report surfaces must not guess Premier/Competitive/Wingman from map.
- Current mode should be labeled `unknown` unless mode metadata is recovered.
- If mode is required for v0.9 acceptance, WP-017E must repair capture/backfill first.

## Proposed WP-017 Work Packages

### WP-017B Controlled Bulk Import Plan / Settings

Objective: finalize operator runbook and settings for the first controlled v0.9 import batch.

Scope:

- no live import/parser/demo download;
- decide whether to use authenticated UI or explicit shell with `TMPDIR`;
- keep `max_demos_per_run=1`;
- define backup/SHA/service/log/storage checklist;
- define exact stop conditions and post-run queries.

### WP-017C First Bulk Import Batch

Objective: run the first controlled real-data batch.

Recommended limit:

- `1` demo per run;
- up to `3` runs total before review;
- stop earlier on any storage/parser/runtime/recommendation anomaly.

Requires explicit live import authorization.

### WP-017D Post-Batch Data/Performance Acceptance

Objective: inspect DB/storage/import jobs/parser artifacts/recommendation evaluations/UI performance after WP-017C.

Acceptance focus:

- exact-date coverage;
- parser artifact coverage;
- recommendation `#5` evaluations;
- no legacy evaluations;
- service/page performance;
- disk growth vs estimate;
- whether cap can safely rise to `2`.

### WP-017E Match Mode Classification Repair If Recoverable

Objective: determine whether Premier/Competitive/Wingman can be extracted from Steam GC/helper/parser metadata and persist or display it honestly.

Possible outcomes:

- recover and backfill mode;
- capture mode only for future imports;
- explicitly label existing rows `unknown`.

Schema change should be avoided unless a first-class mode field or migration is explicitly approved.

### WP-017F Promote Real Data Onboarding To v0.9

Objective: promote `v0.9` only after controlled import batches prove data, storage, parser, recommendation and UI stability.

Required evidence:

- DB SHA before/after;
- import job truth;
- storage growth;
- parser artifact coverage;
- recommendation evaluation stability;
- UI/runtime smoke;
- warnings carried forward.

## Production Safety

- Production DB touched: no.
- Production files touched: no production demo/upload/temp files were changed; this documentation report was created.
- Live import/parser run: no.
- Live Steam/Valve import run: no.
- Demo downloaded: no.
- Parser job run: no.
- Persistent report generated: no.
- Schema changed: no.
- Runtime code changed: no.
- Tests changed: no.
- Commit made: no.

## Schema Change Needed

No schema change is needed for WP-017B planning or the first controlled v0.9 import batches.

For match mode classification, a future repair may need code changes and possibly schema/design work if mode must become a durable first-class product field. Until then, mode should be displayed as `unknown` rather than guessed.

## Can Proceed To WP-017B

Yes.

Proceed to WP-017B as a plan/settings/runbook WP, still without live import/parser/demo download unless the next WP explicitly authorizes those actions.
