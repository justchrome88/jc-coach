# WP-014D Steam Import Runtime and Storage Safety Diagnosis

Date: 2026-07-04

## RESULT

DIAGNOSED

## Scope / Boundaries

Diagnosis-only. No code, tests, production DB rows, demo files, parser jobs, live Steam/Valve import, demo download or commit were performed.

Production DB SHA observed:

- Before diagnosis commands: `8b0799d7da12230018a02a88031006f95e68cf7f3193d4b55d925ead5d3648b0`

## Current Disk Risk

- Root filesystem: `/dev/mapper/ubuntu--vg-ubuntu--lv`, ext4, mounted at `/`.
- Current capacity from `df -h`: `38G` size, `17G` used, `19G` available, `48%`.
- `findmnt -T /opt/jc-coach/data/uploads`: `data/uploads` resolves to `/` on the same root LV; it is not a dedicated filesystem.
- Current `data/uploads`: `3.1G` / `3.07 GiB`, 26 `.dem` files, 0 `.dem.bz2`.
- Before WP-014C, `data/uploads` was about `68K`; WP-014C retained about `3.1G` of raw demos.
- Largest non-upload file on root is `/swap.img` at about `4.0G`; largest app upload is about `400MB`.

The immediate host risk is lower after LVM expansion, but the product risk is unchanged: one button can still consume multiple GB because the runtime has no disk budget, no per-demo preflight and no small batch cap for retain-raw mode.

Safe retain-raw parser development should reserve enough headroom for:

- current retained raw demos: about `3.1G`;
- one active compressed download plus decompressed temp `.dem`;
- one persisted copy in `data/uploads`;
- parser memory/DB/log growth and OS safety margin.

For the current raw-demo size distribution, a conservative minimum is `8G` free before allowing any one-button retained-raw import, with a hard stop that preserves at least `5G` free after each demo. A safer dev target is a dedicated upload volume with `20G+` free if repeated retained-raw parser work is expected. These numbers should be config defaults, not hidden constants.

## Current Storage Layout

- `UPLOAD_DIR` default is `BASE_DIR / "data" / "uploads"` in `app/config.py`.
- `.env.example` documents `UPLOAD_DIR=data/uploads`.
- Steam temp downloads use `tempfile.mkdtemp(prefix="jc-steam-demo-")`, currently under `/tmp`, which is also backed by the host root/tmp setup.
- `_download_demo_file()` downloads the full response into memory via `response.read()`, writes the archive, then for `.bz2` reads the whole archive and writes the decompressed `.dem`.
- `import_demo_file()` copies the decompressed `.dem` into `data/uploads` before parsing.
- Current retain policy `retain_raw_for_parser_development` remains correct; the missing piece is bounded runtime storage use.

Recommendation: move `data/uploads` off root before further live acceptance, preferably to a dedicated mounted volume and point `UPLOAD_DIR` there. A bind mount is operationally cleaner than a symlink because filesystem/free-space checks can target the real mount. A symlink is acceptable only if repair code resolves paths and reports the target filesystem.

## Current Process Risk

- `systemctl status jc-coach --no-pager`: service is active since `2026-07-04 17:33:16 MSK`, PID `116143`, uvicorn on `127.0.0.1:8010`.
- Read-only process scan found uvicorn and no separate active Steam/demo/parser worker.
- FastAPI `BackgroundTasks` runs `_run_steam_import_all_background(job.id)` after the HTTP response.
- There is no app-level cancellation token or shutdown handler that marks active jobs interrupted.
- Long synchronous work is not interrupt-aware: Steam GC helper subprocess, `urlopen(...).read()`, whole-file bz2 decompress, `shutil.copy2`, parser work and DB artifact writes.

This explains why graceful restart waited for background tasks during WP-014C and SIGKILL was needed.

## Current DB Import Job State

`import_jobs` by `job_type/status`:

- `match_history_sync`: 5 `succeeded`, 1 `failed`, 1 `queued`.
- `steam_import_all`: 4 `succeeded`, 1 `failed`, 1 `running`.
- `steam_openid_linked`: 1 `queued`.

Latest relevant jobs:

- `#15`: `steam_import_all`, `running`, created `2026-07-04 14:23:51`, started `2026-07-04 14:23:51.453777`, `finished_at=null`, `result_json=null`, `error_message=null`.
- `#16`: `match_history_sync`, `succeeded`, created `2026-07-04 14:23:51`, finished `2026-07-04 14:23:58.816814`, result collected 20 share codes, inserted 0, duplicates 20, cursor advanced to `CSGO-cAQhC-XL4SM-wWoxt-NNdVO-anUaK`.

Matches:

- `demo`: 18 rows.
- `steam_history`: 41 rows.
- No increase in total match count was observed by WP-014C, but existing `demo` rows and `steam_history` placeholders were updated to point at newly retained WP-014C files.

## Job #15/#16 Analysis

Parent `#15` stayed running because `run_steam_import_all_job()` only commits parent progress at:

- start: status `running`, `started_at`;
- terminal success/failure: final `status`, `finished_at`, `result_json`.

Between those points, the parent performs account checks, creates/runs child sync, marks demo status and downloads/parses demos, but it does not checkpoint parent `result_json`. If the process is killed during downloader/parser work, the final commit never runs and `#15` remains `running` with null result.

Child `#16` succeeded quickly, so its result is durable. Parent progress after `#16` is only inferable from `matches.raw_json`, filesystem timestamps and service logs, not from parent job truth.

`queue_steam_import_all()` also treats any queued/running `steam_import_all` as current. Therefore stale `#15` will block/reuse future one-button starts until explicitly repaired.

## File Inventory Summary

Observed upload inventory:

- 26 `.dem` files.
- 0 `.dem.bz2` files.
- Total `data/uploads`: `3.1G`.
- 13 large WP-014C-style files named `20260704142445...` through `20260704143301...`.
- 13 tiny 7-byte historical files from `20260702...` plus `.gitkeep`.

Largest WP-014C files:

- `400393739` bytes: `20260704142549_84e85746be_CSGO-HRwaS-hoKid-wqu7z-BFh3Y-jkiaB.dem`
- `293225371` bytes: `20260704142925_5cb0be1667_CSGO-CnPaS-Wcyuh-TFC57-Xzotd-CuybE.dem`
- `284903721` bytes: `20260704142648_a9a2ecfc42_CSGO-oQNTD-3obBf-TiUsP-Y9X2y-52DVF.dem`
- `271123862` bytes: `20260704143301_0e38b143b1_CSGO-r5JPP-hv9eO-Uubhz-WOTah-OFSiA.dem`
- `265563694` bytes: `20260704142445_f50a73ee8c_CSGO-cAQhC-XL4SM-wWoxt-NNdVO-anUaK.dem`

Filesystem birth/ctime for the large files is `2026-07-04 17:24:45` through `17:33:01 MSK`, matching the WP-014C run. Their mtime reflects Valve/demo match time in June 2026 because download code applies `Last-Modified`.

## File/DB Consistency Summary

Existing read-only helper result:

- `db_references_file_and_file_exists`: 24 rows.
- `file_exists_without_clear_db_reference`: 14 files.
- `db_references_file_but_file_missing`: 0.

Interpretation:

- 12 large WP-014C files are referenced by both a `demo` row and a corresponding `steam_history` row, hence 24 referencing rows for 12 physical files.
- `20260704143301_0e38b143b1_CSGO-r5JPP-hv9eO-Uubhz-WOTah-OFSiA.dem` is the large likely interrupted WP-014C orphan: it exists in `data/uploads`, but no DB row clearly references it.
- 13 tiny 7-byte files from earlier local/manual attempts are also unreferenced/suspicious.
- Current helper is safe for read-only classification when called with `write_manifest=False`; manifest route writes a report and was not used.

## Root Cause

Primary root cause: the one-button import combines share-code sync, URL resolution, multi-demo download, decompression, raw retention and parser import without runtime storage budgets or parent-job checkpoints.

Contributing causes:

- `settings.steam_sync_max_codes` defaults to 20 and is reused as demo download limit, clamped to 50. This allowed a 20-code live batch.
- `_pending_steam_history_matches()` itself allows up to 50 demos and has no byte budget.
- `_download_demo_file()` has no preflight and writes full archive/decompressed files without size checks.
- `import_demo_file()` copies to `data/uploads` before parsing and has no free-space check before `shutil.copy2`.
- Parent result is written only after the full job completes.
- Graceful shutdown does not mark active import jobs interrupted and blocking sync operations are not cancellation-aware.
- `data/uploads` lives on the root filesystem.

## Required Runtime Safety Guards

Add a storage guard module used by Steam import, downloader and parser copy paths:

- Resolve upload dir and temp dir to real filesystem targets.
- Check `shutil.disk_usage()` before job start.
- Check before URL fetch/download.
- Check after metadata/headers if `Content-Length` exists.
- Check before `.bz2` decompression.
- Check before copying decompressed `.dem` to `data/uploads`.
- Recheck after every imported/skipped/failed demo.
- Refuse or stop with a first-class `disk_budget_exceeded` result, not a generic exception.

Suggested default thresholds for retain-raw mode:

- Minimum free before one-button import: `8 GiB`.
- Minimum free to preserve after each operation: `5 GiB`.
- Required per-demo workspace if size unknown: reserve `1.5 GiB` for archive + decompressed + persisted copy.
- Warn/block when `UPLOAD_DIR` is on `/` and root total is below `50 GiB` or free is below the configured minimum.

These should be operator-configurable through env/settings and visible in docs/runbook.

## Required Batch/Disk Limits

Recommended initial limits for WP-014D repair:

- `STEAM_IMPORT_MAX_DEMOS_PER_RUN`: default `1` or `2` for retained-raw alpha; never inherit `steam_sync_max_codes` directly.
- `STEAM_IMPORT_MAX_BYTES_PER_JOB`: default `1.5 GiB` or `2 GiB`.
- `STEAM_IMPORT_MAX_SINGLE_DEMO_BYTES`: default `600 MiB` when `Content-Length` or metadata is available.
- `STEAM_IMPORT_MIN_FREE_BYTES`: default `8 GiB` preflight.
- `STEAM_IMPORT_PRESERVE_FREE_BYTES`: default `5 GiB` hard floor.

Behavior when budget is exceeded:

- Stop selecting more demos.
- Do not start the next download/decompress/copy.
- Mark current/parent job result with `disk_budget_exceeded`.
- Preserve already persisted successful demo results.
- Return partial-success/failed according to existing taxonomy, with exact counts and budget fields.
- Leave pending demos pending, not failed, when they were not attempted.

## Required Interrupted Job Handling

Add explicit interrupted/stale semantics:

- On app startup or before queuing a new `steam_import_all`, detect old `running` jobs whose process is gone or whose `started_at` exceeds a timeout.
- Mark them as terminal `failed` with `overall_outcome="interrupted"`, `statuses=["interrupted"]`, `finished_at`, and an operator-visible `error_message`.
- Preserve any known partial progress from checkpoints in `result_json`.
- Do not silently reuse stale running jobs as current.
- During graceful shutdown, best-effort mark active in-process jobs as interrupted before process exit.

For current production job `#15`, repair should be an explicit later operator DB mutation, not part of diagnosis. Required safety:

- backup `data/cs2_coach.db`;
- record before/after SHA;
- update only `import_jobs.id=15`;
- set `status='failed'`, `finished_at=<operator repair time>`, `error_message='Interrupted during WP-014C live import safety stop.'`;
- write a `result_json` containing `overall_outcome: interrupted`, `statuses: ["interrupted", "disk_runtime_safety_stop"]`, child job id `16`, known file inventory summary, and note that DB/file cleanup was not performed.

## Required Parent Progress Persistence

Parent `steam_import_all.result_json` should be incrementally persisted after each major event:

- `started`;
- `account_checked`;
- `share_codes_fetch_started`;
- `share_codes_fetched`;
- `demo_queued`;
- `demo_downloading`;
- `demo_downloaded`;
- `demo_decompressing`;
- `demo_stored`;
- `parser_started`;
- `parser_succeeded`;
- `parser_failed`;
- `disk_budget_exceeded`;
- `interrupted`;
- terminal aggregate result.

Use compact JSON with counters and recent events rather than dumping unlimited payloads. Each checkpoint should include `updated_at`, `phase`, `processed/imported/failed/skipped`, `bytes_downloaded`, `bytes_stored`, `budget`, current share code, current file path when known, and child job IDs. Commit after each checkpoint.

## Required Storage/Deployment Recommendation

Before repeat live acceptance:

- Prefer a dedicated volume mounted at `/opt/jc-coach/data/uploads` or another explicit path referenced by `UPLOAD_DIR`.
- Keep root filesystem for OS/app/DB/logs, not unbounded demo retention.
- If using bind mount, document `/etc/fstab`, ownership and rollback.
- If using symlink, code must resolve and report the real target filesystem; bind mount is preferred.
- Keep `data/incoming_demos` separately reviewed; it currently contains a large `287MB` file under `/opt` and also consumes root.

## Required Operator Cleanup/Offload Plan

Diagnosis candidates only; no cleanup performed.

Likely WP-014C files:

- 12 referenced large retained files from `20260704142445` through `20260704143226`.
- 1 unreferenced likely interrupted file: `20260704143301_0e38b143b1_CSGO-r5JPP-hv9eO-Uubhz-WOTah-OFSiA.dem`.

Safe cleanup/offload order for a later authorized operator task:

1. Stop import jobs and verify no active parser/download process.
2. Backup DB and record SHA.
3. Generate read-only storage manifest.
4. Offload/move referenced large files to a dedicated volume or archive path only if DB references will either remain valid via bind mount or be updated in the same backed-up repair.
5. For the unreferenced large interrupted file, prefer archive/offload first, delete only after explicit operator approval and after confirming no DB `demo_file`, `raw_json` or `result_json` reference.
6. Tiny 7-byte unreferenced files can be treated as suspicious cleanup candidates, but should be included in the same explicit cleanup WP.
7. Do not enable automatic raw-demo deletion until parser payload acceptance is complete.

## Minimal Repair Plan for WP-014D Repair

Code repair:

- Add storage budget/preflight helper with filesystem resolution and byte formatting.
- Separate share-code fetch cap from demo download cap.
- Add per-run demo cap and per-job byte budget.
- Add preflight before parent job starts, before each download, before decompression and before copy to uploads.
- Stream downloads to disk with byte counting instead of `response.read()` whole-file buffering.
- Add budget-aware failure type and map it to `disk_budget_exceeded`.
- Add parent checkpoint persistence.
- Add stale/interrupted job detection and explicit interruption marking.
- Make graceful shutdown/job wrapper best-effort mark active jobs interrupted.

Tests:

- Mocked storage budget tests for preflight pass/fail.
- Batch cap test proving 20 share codes do not download 20 demos by default.
- Per-demo budget exceeded before download/decompress/copy.
- Parent checkpoint persistence after account/sync/demo events.
- Stale running job repair on queue/startup helper.
- No live Steam, no real parser, no production DB.

Docs/runbook:

- Update `docs/STEAM_IMPORT.md` with runtime safety limits.
- Add operator cleanup/offload runbook.
- Document recommended `UPLOAD_DIR` dedicated volume/bind mount.
- Document explicit repair steps for job `#15` and orphan file handling.

Optional explicit operator DB/file repair:

- Mark job `#15` interrupted with backup/rollback.
- Offload or delete only explicitly approved files after consistency report.

Optional deployment/storage task:

- Move `data/uploads` to dedicated storage or bind mount before v0.6 live acceptance.

## Can Proceed To Repair

yes

Do not proceed to another live one-button acceptance until runtime storage guards, parent progress persistence and interrupted-job handling are implemented and verified with mocked/local tests.
