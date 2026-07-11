# WP-014C3 Repeat One-Button Steam Import Live Acceptance After TMPDIR Fix Report

Date: 2026-07-04

RESULT: FAIL

The TMPDIR deployment fix worked and the import passed storage preflight. The one-button live path then synced Steam share codes, downloaded/decompressed/stored exactly one demo under the WP-014D1 batch cap, persisted parent checkpoints, and reached a terminal parent state. The run still failed acceptance because parser/import crashed after storing the raw demo:

```text
'played_at_source' is an invalid keyword argument for Match
```

This left one new retained `.dem` file in `data/uploads` and the attempted Steam history row marked `demo_download_error`. No unbounded downloads occurred.

## Backup

Backup path:

```text
data/manual_backups/cs2_coach_before_wp014c3_live_acceptance_20260704_185937.db
```

Backup SHA:

```text
c0f53ed7ae709847c673571da16972bbd31e7623041e9795ca5fcfd1a31496fe  data/manual_backups/cs2_coach_before_wp014c3_live_acceptance_20260704_185937.db
```

## DB SHA

Before live action:

```text
c0f53ed7ae709847c673571da16972bbd31e7623041e9795ca5fcfd1a31496fe  data/cs2_coach.db
```

After live action:

```text
b8b98a3f79d31020dbb4e3c9bb9dba1a47d03371095dfc08fac87bf15010fda0  data/cs2_coach.db
```

## TMPDIR Verification

Systemd environment:

```text
PYTHONUNBUFFERED=1
TMPDIR=/opt/jc-coach/data/tmp
TEMP=/opt/jc-coach/data/tmp
TMP=/opt/jc-coach/data/tmp
```

The running process environment contained the same values. Parent job `#18` result_json confirmed storage guard resolved:

```text
temp_dir=/opt/jc-coach/data/tmp
upload_dir=/opt/jc-coach/data/uploads
same_filesystem=true
```

## Disk / Uploads

Before:

```text
/                         38G size, 19G available, 49% used
/opt/jc-coach/data/tmp    38G size, 19G available, 49% used
data/uploads              3.1G
data/tmp                  4.0K
.dem files                26
```

After:

```text
/                         38G size, 19G available, 50% used
/opt/jc-coach/data/tmp    38G size, 19G available, 50% used
data/uploads              3.4G
data/tmp                  4.0K
.dem files                27
```

New file created:

```text
257492267 data/uploads/20260704160020_28436ba3a5_CSGO-SYSZK-hOFfp-WtBsM-WtsNK-pcy6A.dem
```

No files remained in `data/tmp` after the job; temp staging was cleaned.

## Runtime Safety Config

```text
STEAM_IMPORT_MAX_DEMOS_PER_RUN=1
STEAM_IMPORT_MAX_BYTES_PER_JOB=2147483648
STEAM_IMPORT_MAX_SINGLE_DEMO_BYTES=629145600
STEAM_IMPORT_MIN_FREE_BYTES=8589934592
STEAM_IMPORT_PRESERVE_FREE_BYTES=5368709120
STEAM_IMPORT_UNKNOWN_DEMO_RESERVE_BYTES=1610612736
STEAM_IMPORT_STALE_RUNNING_JOB_SECONDS=3600
```

## Live Action

Performed exactly one authenticated web-route POST to:

```text
POST /settings/imports/pull-all
```

Runtime response:

```text
HTTP 303
Location: /settings/imports?message=Steam%20import%20job%20%2318%20started.%20This%20page%20will%20show%20progress.
```

One-button clicked exactly once: yes. No exact share-code import, manual upload or standalone parser job was run.

## Parent Job

Parent job id: `18`

Before: no running `steam_import_all`; job `#15` was `failed/interrupted`; job `#17` was `failed/storage_preflight_failed`.

After:

```text
id: 18
provider: steam
job_type: steam_import_all
status: failed
started_at: 2026-07-04 15:59:48.733976
finished_at: 2026-07-04 16:00:36.241304
error_message: 1 demo download/parser task(s) failed.
overall_outcome: partial_success
statuses:
  - partial_success
  - duplicate_skipped
  - batch_cap_reached
  - download_failed
  - exact_match_date_unavailable
```

Terminal state not running/null: yes.

Truthful result_json: yes. It records the parser/download failure, batch cap, exact-date unavailable status, child job id, storage usage and progress.

## Parent Checkpoints

Parent checkpoints observed: yes.

Observed phases:

```text
started
account_checked
share_codes_fetch_started
share_codes_fetched
demo_queued
demo_downloading
demo_downloaded
demo_decompressing
parser_started
batch_cap_reached
```

No `parser_succeeded` checkpoint was expected because parser/import failed.

## Child Jobs

New child job:

```text
id=19
job_type=match_history_sync
status=succeeded
sync_outcome=DUPLICATE_ALREADY_IMPORTED
collected=20
inserted=0
duplicates=20
cursor_advanced=true
last_share_code=CSGO-SYSZK-hOFfp-WtBsM-WtsNK-pcy6A
```

The Steam account cursor changed from `CSGO-cAQhC-XL4SM-wWoxt-NNdVO-anUaK` to `CSGO-SYSZK-hOFfp-WtBsM-WtsNK-pcy6A`.

## Batch / Disk Guard

Storage preflight passed: yes.

Batch cap observed: yes.

```text
processed=1
imported=0
failed=1
pending=19
remaining_pending=19
batch_cap_reached=true
```

Disk guard observed: yes. Budget accounting stayed below limits:

```text
downloaded_bytes=156898009
decompressed_bytes=257492267
stored_bytes=257492267
consumed_bytes=671882543
remaining_job_bytes=1475601105
```

No more than `STEAM_IMPORT_MAX_DEMOS_PER_RUN=1` demos were attempted/downloaded: yes.

Remaining pending demos stayed pending: mostly yes. Rows `39-57` were `demo_download_pending`; attempted row `58` was marked `demo_download_error` due parser/import failure.

## Matches / Steam History

Before:

```text
matches_total=59
demo_file_rows=24
steam_history_rows=41
```

After:

```text
matches_total=59
demo_file_rows=24
steam_history_rows=41
```

No new playable `demo` match was persisted.

Changed `import_jobs`: `18`, `19`.

Changed `steam_history` rows: `39-58`.

- Rows `39-57`: set/kept as `demo_download_pending`.
- Row `58`: `demo_download_error`, error `"'played_at_source' is an invalid keyword argument for Match"`, retention status `cleanup_needed`.

Exact match date behavior: not accepted. The parent result reports `exact_match_date_unavailable`; no new parsed match was persisted with exact Steam GC match date because parser/import failed.

## Service Health

`jc-coach.service` remained active.

Manual authenticated GET-only smoke after run:

```text
/settings/imports  200
/matches           200
/coach             200
/dashboard         200
/upload            200
```

Journal since live start showed the single `POST /settings/imports/pull-all` returning `303`; no traceback or HTTP 500 was logged. The service memory rose during parser work and stayed around `1.3G` after the run, which should be watched in the next repair/acceptance pass.

## Safety Summary

- Production DB touched: yes, by the authorized one-button import.
- Production files deleted/moved: no.
- Live Steam/import/parser jobs run: yes, exactly as part of the one authorized one-button import.
- Demo downloads: one.
- Parser jobs: one, as part of the one-button import.
- Schema changed: no.
- One-button clicked exactly once: yes.
- Commit made: no.

## Stale / Interrupted Behavior

No stale running parent job existed before the run. Job `#18` reached terminal failed state and did not become stale. Job `#15` remained failed/interrupted.

## Can v0.6 Be Promoted?

No.

The runtime/storage safety goals are materially improved and the TMPDIR fix is validated, but live acceptance still fails because parser/import raises a schema/model error after storing the raw demo. v0.6 should remain blocked until the `played_at_source` `Match` constructor bug is repaired and a repeat acceptance proves a terminal truthful success/no-new/controlled-failure path without leaving an unreferenced retained demo unexpectedly.

## Remaining Risks / Required Follow-Up

- Repair parser/import path that passes `played_at_source` into `Match`.
- Decide operator handling for the newly retained unreferenced file:
  `data/uploads/20260704160020_28436ba3a5_CSGO-SYSZK-hOFfp-WtBsM-WtsNK-pcy6A.dem`.
- Confirm memory returns to acceptable steady state or document parser memory behavior.
- Repeat live acceptance after parser/import repair.
