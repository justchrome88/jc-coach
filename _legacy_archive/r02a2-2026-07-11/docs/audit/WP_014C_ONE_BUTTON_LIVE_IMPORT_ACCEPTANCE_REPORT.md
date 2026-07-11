# WP-014C One-Button Steam/Valve Live Import Acceptance

Date: 2026-07-04

## RESULT

FAIL

## Product Version Before

`v0.5`

## Product Version After Candidate

Not promoted to `v0.6`.

## Backup

- Backup path: `data/manual_backups/cs2_coach_before_wp014c_live_import_20260704_172046.db`
- Backup SHA: `be2a54fef35227129ae2023931e76d2cf20e100ae09d9ec7e7477f1755526fc2`

## DB SHA

- Before live action: `be2a54fef35227129ae2023931e76d2cf20e100ae09d9ec7e7477f1755526fc2`
- After live action / safety stop: `8b0799d7da12230018a02a88031006f95e68cf7f3193d4b55d925ead5d3648b0`

The production DB was intentionally mutated by the authorized live one-button import. No cleanup or manual DB repair was performed in this WP.

## Disk Usage

- Before: root filesystem about `19G` total, `14G` used, `3.7G` free, `80%`; `data/uploads` was `68K` with 14 files.
- After safety stop: root filesystem about `19G` total, `18G` used, `508M` free, `98%`; `data/uploads` was `3.1G` with 27 files.

## Preflight DB State

- `steam_accounts`: 1.
- Linked Steam account was present and active enough for import; `match_auth_code` present; `last_share_code` present. Secrets were not printed.
- `import_jobs` before live action:
  - `match_history_sync`: 1 failed, 1 queued stale, 4 succeeded.
  - `steam_import_all`: 1 failed, 4 succeeded.
  - `steam_openid_linked`: 1 queued stale.
- Queued/running classification before live action:
  - `steam_openid_linked` job `#1`: stale, non-blocking for primary one-button import.
  - `match_history_sync` job `#10`: stale, non-blocking for primary one-button import.
  - No queued/running `steam_import_all` blocker existed before the button press.
- `matches`: 59 total, 18 `demo`, 41 `steam_history`.
- Active credentialed `test-*@example.test` / `smoke-*@example.test` users: 0.

## Live Action

- Live action performed: yes.
- Button pressed count: 1.
- Button route observed: `POST /settings/imports/pull-all`.
- Immediate UI response: `303 See Other`, then `GET /settings/imports?message=Steam import job #15 started. This page will show progress.` returned `200 OK`.
- No exact share-code debug route was pressed.
- No manual upload/import was run.

## Import Job

- Primary import job id: `15`.
- Job type: `steam_import_all`.
- Final observed status: `running`.
- `finished_at`: null.
- `result_json`: null.
- `error_message`: null.
- Child job id: `16`.
- Child job type: `match_history_sync`.
- Child job final status: `succeeded`.

Because the parent job stayed `running` with no `result_json`, the system did not produce a truthful terminal result for the interrupted live import. This is a P0 blocker for `v0.6` acceptance.

## Job Result Summary

- `overall_outcome`: unavailable; parent `result_json` remained null.
- `statuses`: unavailable; parent `result_json` remained null.
- Accounts processed/skipped: unavailable in parent result.
- Share codes fetched: child match-history job completed, but parent aggregate count was unavailable.
- Duplicates skipped/no-new/errors: unavailable in parent result.
- Demos attempted/downloaded/imported/failed: unavailable in parent result.
- Parser success/failure: unavailable in parent result.

## New Matches

- Matches before live action: 59.
- Matches after safety stop: 59.
- New persisted matches observed: 0.
- Latest `steam_history` row `#59` was updated with retention metadata during the run, but no new parsed/demo match was persisted before the safety stop.

## Demo Retention Result

- Raw demos were retained, as current policy intends.
- However, retention became a runtime safety blocker: `data/uploads` grew from `68K` to `3.1G` during the single one-button run.
- 13 large `.dem` files were observed in `data/uploads` after the safety stop, with the largest about `400 MB`.
- No production demo files were deleted.

## Exact Match Date Result

- No new persisted parsed matches were created during the acceptance window.
- No new exact match-date evidence could be accepted for `v0.6`.
- Existing latest `steam_history` rows still have `played_at = null`; no exact date truth for new imports was proven by this live run.

## Logs Summary

- One `POST /settings/imports/pull-all` was observed at `2026-07-04 17:23:51 MSK`.
- Repeated browser refreshes of `/settings/imports?...job #15 started...` returned `200 OK`.
- No HTTP 500 or traceback was observed in the captured journal window.
- Graceful service restart at `2026-07-04 17:32:19 MSK` did not complete because uvicorn was waiting for background tasks.
- A forced `SIGKILL` was required at `2026-07-04 17:33:15 MSK` to stop the live background import and prevent production disk exhaustion.
- Service restarted successfully at `2026-07-04 17:33:16 MSK`; `GET /` returned `200`.

## Hidden Live Jobs Check

- No repeated `POST /settings/imports/pull-all` was observed.
- No manual upload or exact share-code debug job was observed.
- The single authorized one-button action created jobs `#15` and `#16`.

## Test/Smoke User Contamination Check

- Active credentialed test/smoke users after live action: 0.

## P0 Blockers

- The one-button import can run long enough to fill the production disk under the current retain-raw policy. Root free space dropped from about `3.7G` to `508M`.
- Parent `steam_import_all` job `#15` remained `running` with null `result_json` after operational interruption.
- Graceful service restart could not stop the background import promptly; force kill was required.
- No terminal success/no-new/partial/error status was recorded for the parent job before the safety stop.
- No new persisted parsed match evidence was produced before the safety stop.

## P1 Risks

- The current one-button path appears to download multiple large demos in one run without a visible disk budget or batch cap.
- There is no operator-facing progress/result checkpoint while large downloads are in progress.
- Retain-raw remains correct for parser development, but it needs disk budget controls before live acceptance can pass.
- Stale queued jobs already exist historically and the interrupted parent job `#15` is now another stale `running` operator cleanup item.

## Production Files Deleted

No.

## Production DB Touched

Yes. The authorized live import created/updated import-job and Steam/match metadata rows. No manual DB cleanup was performed.

## Live Steam/Import/Parser Jobs Run

Yes. Exactly one authorized primary one-button live import was run. No additional live import/parser jobs were intentionally started.

## Schema Changed

No.

## Can Promote To v0.6

No.

## Next Recommended WP

`WP-014D Steam Import Runtime Safety Repair`

Minimum scope:

- add a disk-space preflight/budget guard before demo download;
- cap one-button live batch size or make it operator-configurable;
- persist parent `steam_import_all` progress/result_json incrementally enough to diagnose interrupted runs;
- mark interrupted/stale running jobs truthfully on next operator action or via explicit safe operator repair;
- make graceful shutdown cancel or fail running import jobs cleanly;
- keep raw-demo deletion disabled by default, but provide an operator runbook for safe archive/cleanup after backup.
