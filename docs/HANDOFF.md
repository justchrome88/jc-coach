# Handoff

Last updated: 2026-07-04.

## Current State

- Current Product Version: `v0.5`
- Current WP: `WP-014D Steam Import Runtime Safety Repair`
- Next Target Version: `v0.6`
- Mode after WP-011B: governance/tooling layer exists; product logic and DB were not intentionally changed.
- Runtime: `jc-coach.service` should be checked at pass start with `systemctl status jc-coach --no-pager`.
- Owner recovery state: production owner currently resolves to `justchrome88@yandex.ru` (`users.id=17`) after historical `test-*@example.test` and `smoke-*@example.test` users were manually deactivated and had password hashes cleared.
- WP-013 runtime smoke: `PASS_WITH_WARNINGS`; service restart and read-only smoke passed on 2026-07-04 with DB SHA `0850e6a28b08e4150cff43e10fbd39f38bef3e3ca3e494ab5a534c22738a230d`. Full owner manual browser checklist remains operator evidence to record.
- WP-014A Steam/Valve import diagnosis: `DIAGNOSED`; report is `docs/audit/WP_014A_STEAM_VALVE_IMPORT_DIAGNOSIS.md`. Current primary button is `/settings/imports` -> `POST /settings/imports/pull-all` -> `steam_import_all` background job. Repair is required before `v0.6`: explicit outcome taxonomy, import_job coverage for download/parser paths, exact match-date truth, and raw demo cleanup after successful parse/persist.
- WP-014B1 import-job truth/status repair: completed without schema change or production DB mutation. `steam_import_all` now writes standardized outcome/status taxonomy to `result_json`, avoids clean `succeeded` for missing-code/download/parser/partial cases, and exact share-code import now creates a `share_code_import` tracking job before downloader/parser work.
- WP-014B2 exact match-date truth repair: completed without schema change or production DB mutation. Primary Steam import treats Steam GC `match_time` as the only exact Steam match date, clears imported `Match.played_at` when GC time is unavailable instead of retaining file-mtime fallback, records `match_date_status/source`, and uses exact-only imported dates for Steam freshness.
- WP-014B3 demo retention policy repair: completed without schema change, production DB mutation or production file deletion. Current policy is explicit `retain_raw_for_parser_development`; `delete_after_success` remains disabled; successful/failed imports record retention metadata and storage reporting has read-only file/DB consistency classification.
- WP-014C one-button live acceptance: `FAIL`. One authorized click on `/settings/imports` -> `POST /settings/imports/pull-all` created `steam_import_all` job `#15` and `match_history_sync` job `#16`. The parent job stayed `running` with null `result_json`, downloaded/retained raw demos grew `data/uploads` from `68K` to `3.1G`, root free space fell to `508M`, graceful restart hung waiting for background tasks, and a force kill was required to protect disk. No production files were deleted and no code/schema changes were made. Report: `docs/audit/WP_014C_ONE_BUTTON_LIVE_IMPORT_ACCEPTANCE_REPORT.md`.

## Last Incident Summary

`BUGFIX-001` diagnosed `/coach` runtime 500 as a stale uvicorn process after Stage 9 route/template changes. Current source was consistent; the running process had old route code while templates were updated on disk. Required operational lesson: after Python route/template deployment, restart the service and smoke the already-running runtime. Do not treat TestClient success alone as runtime freshness evidence.

## Current Blockers

- Production/friends readiness remains blocked by import acceptance, import disk/runtime safety, migration discipline hardening, operational visibility and release gates.
- Recommendation planner / verified top problem is not implemented.
- Parser, Steam, metrics and AI paths remain governed by confidence and no-live-job restrictions unless a WP explicitly authorizes them.

## Next WP

`WP-014D Steam Import Runtime Safety Repair` targeting a repeatable `v0.6` import acceptance attempt.

The next active WP is `WP-014D Steam Import Runtime Safety Repair`.

Expected focus: repair the WP-014C live blockers before any repeat live acceptance. Required areas are disk-space preflight/budget guard, one-button batch limit or operator-configurable cap, incremental parent job progress/result truth, clean handling of interrupted/stale running jobs, and graceful shutdown cancellation/failure behavior. Do not run another live Steam/import/parser job unless the WP explicitly authorizes it with DB SHA, backup evidence and disk-cap safeguards.

Roadmap and WP wiring:

- Human docs entrypoint: `docs/README.md`
- Human docs index: `docs/project_management/DOCS_INDEX.md`
- Version roadmap: `docs/project_management/VERSION_ROADMAP.md`
- Work package backlog: `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- Acceptance matrix: `docs/project_management/ACCEPTANCE_MATRIX.md`
- Docs map: `docs/project_management/DOCS_MAP.md`

Next planned versions:

- `v0.6`: `WP-014 Import Acceptance`
- `v0.7`: `WP-015 Metrics Correctness`
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
