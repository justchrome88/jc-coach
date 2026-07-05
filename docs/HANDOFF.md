# Handoff

Last updated: 2026-07-05.

## Current State

- Current Product Version: `v0.8`
- Current WP: `WP-017G Data Integrity Acceptance`
- Next Target Version: `v0.9`
- Mode after WP-011B: governance/tooling layer exists; product logic and DB were not intentionally changed.
- Runtime: `jc-coach.service` should be checked at pass start with `systemctl status jc-coach --no-pager`.
- Owner recovery state: production owner currently resolves to `justchrome88@yandex.ru` (`users.id=17`) after historical `test-*@example.test` and `smoke-*@example.test` users were manually deactivated and had password hashes cleared.
- WP-013 runtime smoke: `PASS_WITH_WARNINGS`; service restart and read-only smoke passed on 2026-07-04 with DB SHA `0850e6a28b08e4150cff43e10fbd39f38bef3e3ca3e494ab5a534c22738a230d`. Full owner manual browser checklist remains operator evidence to record.
- WP-014A Steam/Valve import diagnosis: `DIAGNOSED`; report is `docs/audit/WP_014A_STEAM_VALVE_IMPORT_DIAGNOSIS.md`. Current primary button is `/settings/imports` -> `POST /settings/imports/pull-all` -> `steam_import_all` background job. Repair is required before `v0.6`: explicit outcome taxonomy, import_job coverage for download/parser paths, exact match-date truth, and raw demo cleanup after successful parse/persist.
- WP-014B1 import-job truth/status repair: completed without schema change or production DB mutation. `steam_import_all` now writes standardized outcome/status taxonomy to `result_json`, avoids clean `succeeded` for missing-code/download/parser/partial cases, and exact share-code import now creates a `share_code_import` tracking job before downloader/parser work.
- WP-014B2 exact match-date truth repair: completed without schema change or production DB mutation. Primary Steam import treats Steam GC `match_time` as the only exact Steam match date, clears imported `Match.played_at` when GC time is unavailable instead of retaining file-mtime fallback, records `match_date_status/source`, and uses exact-only imported dates for Steam freshness.
- WP-014B3 demo retention policy repair: completed without schema change, production DB mutation or production file deletion. Current policy is explicit `retain_raw_for_parser_development`; `delete_after_success` remains disabled; successful/failed imports record retention metadata and storage reporting has read-only file/DB consistency classification.
- WP-014C one-button live acceptance: `FAIL`. One authorized click on `/settings/imports` -> `POST /settings/imports/pull-all` created `steam_import_all` job `#15` and `match_history_sync` job `#16`. The parent job stayed `running` with null `result_json`, downloaded/retained raw demos grew `data/uploads` from `68K` to `3.1G`, root free space fell to `508M`, graceful restart hung waiting for background tasks, and a force kill was required to protect disk. No production files were deleted and no code/schema changes were made. Report: `docs/audit/WP_014C_ONE_BUTTON_LIVE_IMPORT_ACCEPTANCE_REPORT.md`.
- WP-014D1 storage guard/batch cap repair: completed without live Steam/import/parser jobs, production DB mutation or production file cleanup. Added configurable disk preflight, per-run demo cap, per-job byte budget, per-demo max size, preserve-free checks before download/decompression/upload copy, streamed download with byte counting, and budget-aware result statuses.
- WP-014D2 parent checkpoint/interruption repair: completed without live Steam/import/parser jobs, production DB mutation or production file cleanup. Parent `steam_import_all` jobs now commit bounded progress checkpoints, queue-time stale running parent jobs are marked failed/interrupted before a new one is queued, non-stale running jobs remain blocking, startup repair is available but disabled by default, and `scripts/repair_stale_steam_import_job.py` provides explicit operator repair for job `#15` after backup/SHA evidence.
- WP-014D3 operator stale job repair: completed with backup/SHA evidence. Production `import_jobs.id=15` was the only logical `import_jobs` row changed; it is now `failed` with `result_json.overall_outcome="interrupted"`. No live Steam/import/parser job ran, and no production demo files were deleted or moved. Report: `docs/audit/WP_014D3_OPERATOR_REPAIR_STALE_JOB15_REPORT.md`.
- WP-014C3 repeat one-button live acceptance after TMPDIR fix: `FAIL`, but storage safety was proven. Service TMPDIR resolved to `data/tmp`, storage preflight passed, one authorized click downloaded/stored exactly one raw demo under the batch cap, parent job `#18` reached terminal failed state with checkpoints and bounded disk growth. Failure cause was parser/import model mismatch: `played_at_source` metadata was passed to `Match(...)`. New retained raw demo: `data/uploads/20260704160020_28436ba3a5_CSGO-SYSZK-hOFfp-WtBsM-WtsNK-pcy6A.dem`; do not delete or parse it outside an explicitly authorized WP.
- WP-014E parser/import model compatibility repair: completed without schema change, live Steam/import/parser jobs, production DB mutation or production file cleanup. `played_at_source` and date truth metadata remain in `raw_json`/result payloads and are filtered out of `Match` constructor kwargs.
- WP-014C4 repeat one-button live acceptance after parser repair: `PASS_WITH_WARNINGS`. One authorized click created parent job `#20`, storage/TMPDIR guard passed, batch cap limited the run to exactly one demo, parser/import succeeded, exact date truth was persisted via `steam_gc_match_time`, parent `result_json` reached terminal truthful `batch_cap_reached` with `success` and `exact_match_date_available`, service stayed healthy and disk growth was bounded. This promotes controlled personal import acceptance to `v0.6`. Warnings carried forward: coarse `ImportJob.status`, uploads/temp on root, raw demos retained, parser memory peak should be watched, and friends/public readiness remains blocked.
- WP-015A diagnosis and WP-015A1 repair reconciled historical match-date truth without reset/resync, live Steam/API, parser jobs, schema changes or production file changes. Rows `21-24` were exact-backfilled from linked `steam_history` rows `5-8`; rows `1-8` and `59` were normalized as non-playable placeholder metadata; rows `37-38` remain playable approximate/file-mtime fallback. Current playable date truth after WP-017A is 18 exact, 2 approximate, 0 unknown.
- WP-015B diagnosed metrics correctness and found no DB reset requirement: all then-current 19 playable demo rows had parser artifacts, `steam_history` placeholders are excluded from playable metrics, and the main v0.7 risk was confidence/date-window gating.
- WP-015C implemented metric confidence and exact-date window guardrails without schema changes, production DB mutation, live import or parser jobs. Dashboard/stats/coach/report/recommendation/AI paths now use exact-date playable rows for recent/trend/form windows, expose exact/approximate/excluded counts, and carry confidence metadata for weak or unavailable metrics.
- WP-015C-PERF diagnosed blocker-level latency from repeated `json.loads` of large `matches.raw_json` payloads. WP-015C1 repaired it with request/helper-level `MetricContext` caching and removed duplicated confidence/date-window work. Runtime builders are now sub-second in local production-DB measurements; `/coach` remains the heaviest because artifact overview still loads many ORM rows.
- WP-015D runtime metrics acceptance completed / `PASS_WITH_WARNINGS` and promoted Metrics Correctness to `v0.7`. Accepted: confidence/date-window gating, unsupported metric suppression/relabeling, approximate row exclusion from exact windows, AI confidence metadata, repaired page-builder performance, clean service restart, unchanged DB SHA, and no production DB/file/schema/live job impact. Carry warnings: no direct post-restart authenticated browser timings from Codex, old recommendation baseline `#1` lacks stored confidence metadata, report-write acceptance deferred, `/coach` artifact overview still loads many ORM rows, weak metrics remain weak, `ImportJob.status` is coarse, uploads/tmp remain on root.
- WP-016A diagnosed recommendation loop state: production recommendations `#1-#4` are legacy, active `#1` uses non-playable `steam_history` placeholder baseline IDs, lacks baseline confidence, and existing evaluations lack `metric_confidence`.
- WP-016B implemented the legacy refresh foundation without running the production refresh: legacy recommendation health detection, read/UI/API/report labeling, automatic evaluation skip for legacy active recommendations, and explicit category restart support that archives legacy records and creates confidence-aware baselines from playable exact-date rows.
- WP-016C controlled production refresh completed for `survival`: DB backup was created, `restart_recommendation_category(db, "survival")` was run exactly once, old recommendation `#1` was archived/preserved, new active recommendation `#5` has playable exact-date baseline IDs `23-36,70`, confidence metadata, real target metrics and `recommendation_health.needs_refresh=false`. No evaluations, reports, imports, parser jobs or demo files were created.
- WP-016D runtime acceptance completed / `PASS_WITH_WARNINGS`: active survival recommendation `#5` is armed, confidence-aware and read-safe, but no exact playable match exists after `start_after_match_id=70`, so next-match evaluation was not exercised.
- WP-016E controlled next-match evaluation attempt failed safely before download/import/parser work. A DB backup was created, then one service-level `import_all_available_steam_matches(db)` attempt created job `#22` and stopped at `storage_preflight_failed` because the shell process resolved `temp_dir` to `/tmp`, not the systemd `TMPDIR=/opt/jc-coach/data/tmp`. Counts remained 5 recommendations, 75 evaluations, 0 reports; recommendation `#5` still has 0 evaluations.
- WP-016E2 controlled next-match evaluation retry completed as `BLOCKED_NO_NEW_MATCH`. A DB backup was created, then one service-level `import_all_available_steam_matches(db)` attempt was run with explicit `TMPDIR/TEMP/TMP=/opt/jc-coach/data/tmp`. Parent job `#23` and child sync job `#24` succeeded with `overall_outcome=no_new`; no demo was downloaded, no parser/evaluation/report ran, and recommendation `#5` still has 0 evaluations.
- WP-016E3 controlled next-match evaluation after a real Competitive match completed as `FAILED`. A DB backup was created, then one guarded service-level import was run with explicit `TMPDIR/TEMP/TMP=/opt/jc-coach/data/tmp`. Parent job `#25` and child sync job `#26` succeeded; exactly one new Dust2 demo was retained and parsed as playable exact-date match `#72`. The recommendation loop did not complete because recommendation `#5` still has 0 evaluations and progress remains waiting.
- WP-016E4 post-import recommendation evaluation repair completed / `REPAIRED_AND_EVALUATED`. The parser/import completion path now evaluates the specific newly imported match through `evaluate_recommendations_for_match(...)`. After backup, a controlled production evaluation for existing match `#72` created evaluation `#76` for recommendation `#5` with `metric_confidence`; progress now has 1 completed match and legacy recommendations `#1/#3/#4` received no new evaluations.
- WP-016F documentation/status promotion completed / `PROMOTED`. Recommendation Loop Acceptance is now `v0.8` for controlled personal MVP runtime: `recommendation #5 -> real exact-date Dust2 match #72 -> evaluation #76 with metric_confidence -> progress completed_matches=1`. This does not validate recommendation planner quality, refresh all categories, or make the product friends/public-ready.
- WP-017A real data onboarding diagnosis completed / `DIAGNOSED`. Current baseline: 72 matches, 20 playable parsed demos, 18 exact playable dates, 2 approximate playable dates, 52 steam_history placeholders, about 3.8G in uploads, about 17.07 GiB root free, accepted recommendation `#5` with 1 green evaluation, and all persisted playable match modes classified as unknown because Premier/Competitive/Wingman is not reliably stored.
- WP-017B controlled bulk import plan completed / `PLANNED`. Runbook: keep `STEAM_IMPORT_MAX_DEMOS_PER_RUN=1`, run at most three one-demo attempts in WP-017C, stop after every attempt, require pre/post DB SHA, backup before first live run, storage/service/job/recommendation checks, explicit `TMPDIR/TEMP/TMP=/opt/jc-coach/data/tmp` for shell fallback, and do not raise cap until WP-017D acceptance.
- WP-017C first controlled bulk import batch completed / `PASS_WITH_WARNINGS`. Backup `data/manual_backups/cs2_coach_before_wp017c_first_batch_20260705_015315.db` was created. Authenticated UI was unavailable to Codex (`GET /settings/imports` redirected to `/login`, unauthenticated `POST /settings/imports/pull-all` returned `403`), so the authorized shell fallback ran exactly once with explicit temp env. Parent job `#27` and child sync job `#28` succeeded as `PASS_NO_NEW_MATCH`; no new share code, demo download, parser run, playable match or recommendation evaluation occurred. DB SHA moved from `36ccd84dc5c695af1c75a74f8d1059ade68a2a0355bb43aca1a7b473dd68f320` to `809fdd5a645baac27b89e8e36b9d22f186249cab14d133314382404eac283ddf` due authorized job writes. Uploads stayed unchanged, `data/tmp` stayed empty, service stayed active, legacy `#3/#4` evaluation counts stayed unchanged, and match mode remains unknown.
- WP-017C2 controlled import after a new Valve match completed / `PASS_ONE_DEMO_IMPORTED_AND_EVALUATED`. Backup `data/manual_backups/cs2_coach_before_wp017c2_after_new_match_20260705_030831.db` was created. One shell-fallback attempt with explicit temp env created parent job `#29` and child sync job `#30`; Steam returned two new share codes, one demo was downloaded/retained/parsed under cap `1`, and playable exact-date Overpass match `#75` was created from `steam_gc_match_time`. Parent job `#29` is `failed` only because `overall_outcome=batch_cap_reached` left one pending placeholder `#73`. Recommendation `#5` received evaluation `#77` with `metric_confidence`, progress is now `2/10`, legacy `#3/#4` stayed unchanged, schema stayed unchanged, `data/tmp` returned to `0` bytes, and raw demos were not deleted/moved/compressed.
- WP-017D post-batch diagnosis completed / `ACCEPT_WITH_REPAIR_REQUIRED`. WP-017C/C2 import, parser, storage and manual evaluation evidence was healthy, but automatic post-import recommendation evaluation in the Steam path was unreliable: `import_demo_file(...)` evaluated before `_apply_primary_steam_date_truth(...)` made the imported match exact-date eligible. Pending placeholder `#73` and cap raise remained blocked.
- WP-017E auto-evaluation trigger repair completed / `REPAIRED`. Steam downloader imports now pass `evaluate_recommendations=False` to parser import, apply/commit/refresh authoritative Steam date truth, then run `evaluate_recommendations_for_match(...)` and carry compact `recommendation_evaluations` metadata into demo download results. Tests cover exact-date auto-evaluation, batch-cap metadata, duplicate protection, legacy skip and non-exact gating. No production DB/live Steam/import/parser/manual evaluator work ran, pending `#73` was not processed, schema and cap were unchanged.
- WP-017F controlled pending share code `#73` import completed / `PASS_PENDING_73_IMPORTED_AND_AUTO_EVALUATED`. Backup `data/manual_backups/cs2_coach_before_wp017f_pending_73_import_20260705_034135.db` was created. One targeted pending-demo attempt processed `CSGO-owEoV-4o9Uj-kK5Fp-4zYKz-UqDZG`, downloaded/retained/parsed exactly one demo as playable exact-date Mirage match `#76`, and automatic evaluation `#78` for recommendation `#5` was created with `metric_confidence`; progress is now `3/10`. No manual evaluator ran, legacy `#3/#4` stayed unchanged, cap stayed `1`, schema stayed unchanged, raw demos were not deleted/moved/compressed, and `data/tmp` returned to `0` bytes. The narrow pending-demo path did not create a new parent `steam_import_all` job; metadata is in the returned service result and placeholder raw JSON.

## Last Incident Summary

`BUGFIX-001` diagnosed `/coach` runtime 500 as a stale uvicorn process after Stage 9 route/template changes. Current source was consistent; the running process had old route code while templates were updated on disk. Required operational lesson: after Python route/template deployment, restart the service and smoke the already-running runtime. Do not treat TestClient success alone as runtime freshness evidence.

## Current Blockers

- Production/friends readiness remains blocked by import acceptance, import disk/runtime safety, migration discipline hardening, operational visibility and release gates.
- Recommendation planner / verified top problem is not implemented.
- Parser, Steam, metrics and AI paths remain governed by confidence and no-live-job restrictions unless a WP explicitly authorizes them.

## Next WP

`WP-017G Data Integrity Acceptance` targeting `v0.9`.

WP-017G should review WP-017F as a read-only data integrity and runtime acceptance gate. Use:

- `docs/audit/WP_017C_FIRST_CONTROLLED_BULK_IMPORT_BATCH_REPORT.md`
- `docs/audit/WP_017C2_CONTROLLED_IMPORT_AFTER_NEW_MATCH_REPORT.md`
- `docs/audit/WP_017D_POST_BATCH_ACCEPTANCE_AND_EVALUATION_TRIGGER_DIAGNOSIS.md`
- `docs/audit/WP_017E_AUTO_EVALUATION_TRIGGER_REPAIR_REPORT.md`
- `docs/audit/WP_017F_CONTROLLED_PENDING_73_IMPORT_REPORT.md`

Expected focus: verify DB/storage/parser/recommendation consistency after matches `#75/#76`, confirm automatic evaluation `#78` and metadata surfaces, account for the lack of parent job result JSON in the targeted pending-demo path, keep match mode unknown unless persisted data proves otherwise, and decide whether a later WP may promote v0.9 or plan a cap change. Do not run live imports, delete/move raw demos, change schema, run manual evaluator, or create persistent app reports unless a later WP explicitly authorizes it.

Roadmap and WP wiring:

- Human docs entrypoint: `docs/README.md`
- Human docs index: `docs/project_management/DOCS_INDEX.md`
- Version roadmap: `docs/project_management/VERSION_ROADMAP.md`
- Work package backlog: `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- Acceptance matrix: `docs/project_management/ACCEPTANCE_MATRIX.md`
- Docs map: `docs/project_management/DOCS_MAP.md`

Next planned versions:

- `v0.6`: `WP-014 Import Acceptance` completed / accepted with warnings
- `v0.7`: `WP-015 Metrics Correctness` completed / accepted with warnings
- `v0.8`: `WP-016 Recommendation Loop Acceptance` completed / promoted
- `v0.9`: Real Data Onboarding / Bulk Demo Usage
- `v0.10`: Coach Quality Calibration
- `v0.11`: Personal Daily Use UX
- `v0.12`: Deployment / Backup / Storage Hardening
- `v1.0`: Personal MVP Lock

## Commands To Run First

```bash
git status --short
git log --oneline -20
sha256sum data/cs2_coach.db
systemctl status jc-coach --no-pager
python3 scripts/project_gate.py preflight
python3 scripts/project_gate.py changed
python3 scripts/project_gate.py required-checks
```

If `python` is unavailable on the host, use `python3` for `scripts/project_gate.py` and report the environment gap.

## Do Not Do

- Do not change product logic outside the active WP.
- Do not change DB schema/data without explicit authorization.
- Do not run live AI, Steam, import, parser or production jobs unless explicitly authorized.
- Do not restart `jc-coach.service` unless the task requires runtime deployment/smoke and the user allows it.
- Do not commit unless the user explicitly asks.
- Do not touch `/coach`, import, metrics or recommendation logic unless the active WP says so.
