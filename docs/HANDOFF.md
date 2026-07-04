# Handoff

Last updated: 2026-07-04.

## Current State

- Current Product Version: `v0.7`
- Current WP: `WP-016 Recommendation Loop Acceptance` in progress; survival recommendation `#5` is armed and waiting for a post-refresh playable exact-date match.
- Next Target Version: `v0.8`
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
- WP-015A diagnosis and WP-015A1 repair reconciled historical match-date truth without reset/resync, live Steam/API, parser jobs, schema changes or production file changes. Rows `21-24` were exact-backfilled from linked `steam_history` rows `5-8`; rows `1-8` and `59` were normalized as non-playable placeholder metadata; rows `37-38` remain playable approximate/file-mtime fallback. Current playable date truth: 17 exact, 2 approximate, 0 unknown.
- WP-015B diagnosed metrics correctness and found no DB reset requirement: all 19 playable demo rows have parser artifacts, `steam_history` placeholders are excluded from playable metrics, and the main v0.7 risk is confidence/date-window gating.
- WP-015C implemented metric confidence and exact-date window guardrails without schema changes, production DB mutation, live import or parser jobs. Dashboard/stats/coach/report/recommendation/AI paths now use exact-date playable rows for recent/trend/form windows, expose exact/approximate/excluded counts, and carry confidence metadata for weak or unavailable metrics.
- WP-015C-PERF diagnosed blocker-level latency from repeated `json.loads` of large `matches.raw_json` payloads. WP-015C1 repaired it with request/helper-level `MetricContext` caching and removed duplicated confidence/date-window work. Runtime builders are now sub-second in local production-DB measurements; `/coach` remains the heaviest because artifact overview still loads many ORM rows.
- WP-015D runtime metrics acceptance completed / `PASS_WITH_WARNINGS` and promoted Metrics Correctness to `v0.7`. Accepted: confidence/date-window gating, unsupported metric suppression/relabeling, approximate row exclusion from exact windows, AI confidence metadata, repaired page-builder performance, clean service restart, unchanged DB SHA, and no production DB/file/schema/live job impact. Carry warnings: no direct post-restart authenticated browser timings from Codex, old recommendation baseline `#1` lacks stored confidence metadata, report-write acceptance deferred, `/coach` artifact overview still loads many ORM rows, weak metrics remain weak, `ImportJob.status` is coarse, uploads/tmp remain on root.
- WP-016A diagnosed recommendation loop state: production recommendations `#1-#4` are legacy, active `#1` uses non-playable `steam_history` placeholder baseline IDs, lacks baseline confidence, and existing evaluations lack `metric_confidence`.
- WP-016B implemented the legacy refresh foundation without running the production refresh: legacy recommendation health detection, read/UI/API/report labeling, automatic evaluation skip for legacy active recommendations, and explicit category restart support that archives legacy records and creates confidence-aware baselines from playable exact-date rows.
- WP-016C controlled production refresh completed for `survival`: DB backup was created, `restart_recommendation_category(db, "survival")` was run exactly once, old recommendation `#1` was archived/preserved, new active recommendation `#5` has playable exact-date baseline IDs `23-36,70`, confidence metadata, real target metrics and `recommendation_health.needs_refresh=false`. No evaluations, reports, imports, parser jobs or demo files were created.
- WP-016D runtime acceptance completed / `PASS_WITH_WARNINGS`: active survival recommendation `#5` is armed, confidence-aware and read-safe, but no exact playable match exists after `start_after_match_id=70`, so next-match evaluation was not exercised.
- WP-016E controlled next-match evaluation attempt failed safely before download/import/parser work. A DB backup was created, then one service-level `import_all_available_steam_matches(db)` attempt created job `#22` and stopped at `storage_preflight_failed` because the shell process resolved `temp_dir` to `/tmp`, not the systemd `TMPDIR=/opt/jc-coach/data/tmp`. Counts remained 5 recommendations, 75 evaluations, 0 reports; recommendation `#5` still has 0 evaluations.
- WP-016E2 controlled next-match evaluation retry completed as `BLOCKED_NO_NEW_MATCH`. A DB backup was created, then one service-level `import_all_available_steam_matches(db)` attempt was run with explicit `TMPDIR/TEMP/TMP=/opt/jc-coach/data/tmp`. Parent job `#23` and child sync job `#24` succeeded with `overall_outcome=no_new`; no demo was downloaded, no parser/evaluation/report ran, and recommendation `#5` still has 0 evaluations.

## Last Incident Summary

`BUGFIX-001` diagnosed `/coach` runtime 500 as a stale uvicorn process after Stage 9 route/template changes. Current source was consistent; the running process had old route code while templates were updated on disk. Required operational lesson: after Python route/template deployment, restart the service and smoke the already-running runtime. Do not treat TestClient success alone as runtime freshness evidence.

## Current Blockers

- Production/friends readiness remains blocked by import acceptance, import disk/runtime safety, migration discipline hardening, operational visibility and release gates.
- Recommendation planner / verified top problem is not implemented.
- Parser, Steam, metrics and AI paths remain governed by confidence and no-live-job restrictions unless a WP explicitly authorizes them.

## Next WP

`WP-016 Recommendation Loop Acceptance` targeting `v0.8`.

WP-016 has started. The survival loop is armed, but v0.8 cannot be promoted until one real post-refresh playable exact-date match is imported and evaluated for recommendation `#5`. The next controlled attempt should wait until a new Steam match is expected and must use the guarded one-run path with `TMPDIR=/opt/jc-coach/data/tmp TEMP=/opt/jc-coach/data/tmp TMP=/opt/jc-coach/data/tmp` for service-level invocation; do not run live Steam/import/parser work unless explicitly authorized.

Expected focus: accept recommendation -> next match -> evaluation -> progress as a coherent loop using the accepted v0.7 metric confidence rules. Do not run live Steam/import/parser work unless a future WP explicitly authorizes it with DB SHA, backup evidence and disk-cap safeguards.

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
- `v0.8`: `WP-016 Recommendation Loop Acceptance`
- `v0.9`: `WP-017 Personal Beta`
- `v1.0`: `WP-018 Trusted MVP`

## Commands To Run First

```bash
git status --short
git log --oneline -12
sha256sum data/cs2_coach.db
systemctl status jc-coach --no-pager
python scripts/project_gate.py preflight
python scripts/project_gate.py changed
python scripts/project_gate.py required-checks
```

If `python` is unavailable on the host, use `python3` for `scripts/project_gate.py` and report the environment gap.

## Do Not Do

- Do not change product logic outside the active WP.
- Do not change DB schema/data without explicit authorization.
- Do not run live AI, Steam, import, parser or production jobs unless explicitly authorized.
- Do not restart `jc-coach.service` unless the task requires runtime deployment/smoke and the user allows it.
- Do not commit unless the user explicitly asks.
- Do not touch `/coach`, import, metrics or recommendation logic unless the active WP says so.
