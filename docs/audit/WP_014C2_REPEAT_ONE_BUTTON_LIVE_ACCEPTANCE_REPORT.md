# WP-014C2 Repeat One-Button Steam Import Live Acceptance Report

Date: 2026-07-04

RESULT: FAIL

This was a controlled safety failure, not a runtime/disk incident. The authorized one-button route was invoked exactly once and terminated immediately with `storage_preflight_failed` because `/tmp` had about `1.4G` free, below `STEAM_IMPORT_MIN_FREE_BYTES=8GiB`. No demos were downloaded, no parser work ran, no production demo files were deleted or moved, and `data/uploads` did not grow.

## Backup

Backup path:

```text
data/manual_backups/cs2_coach_before_wp014c2_live_acceptance_20260704_184514.db
```

Backup SHA:

```text
5a7aecf4cc0488c978c10eb7aecc5169aad0d277f52a15ec393fb0287b2a736e  data/manual_backups/cs2_coach_before_wp014c2_live_acceptance_20260704_184514.db
```

## DB SHA

Before live action:

```text
5a7aecf4cc0488c978c10eb7aecc5169aad0d277f52a15ec393fb0287b2a736e  data/cs2_coach.db
```

After live action:

```text
c0f53ed7ae709847c673571da16972bbd31e7623041e9795ca5fcfd1a31496fe  data/cs2_coach.db
```

The DB changed only by creating/updating parent `steam_import_all` job `#17`.

## Disk / Uploads

Before:

```text
/       38G size, 19G available, 49% used
/tmp    1.7G size, 1.4G available, 16% used
data/uploads: 3.1G
.dem files: 26
```

After:

```text
/       38G size, 19G available, 49% used
/tmp    1.7G size, 1.4G available, 16% used
data/uploads: 3.1G
.dem files: 26
```

New files created during run: none.

Files modified under `data/uploads` since live start: none.

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
Location: /settings/imports?message=Steam%20import%20job%20%2317%20started.%20This%20page%20will%20show%20progress.
```

One-button clicked exactly once: yes. The action was a single scripted authenticated POST to the same web route used by the button. No exact share-code import, manual upload or standalone parser job was run.

## Parent Job

Parent job id: `17`

Before: no running `steam_import_all`; job `#15` was already `failed/interrupted` after WP-014D3.

After:

```text
id: 17
provider: steam
job_type: steam_import_all
status: failed
started_at: 2026-07-04 15:46:21.603773
finished_at: 2026-07-04 15:46:21.603786
error_message: Steam import storage preflight failed for temp_dir: free space is below minimum.
```

Result summary:

```json
{
  "overall_outcome": "storage_preflight_failed",
  "statuses": ["storage_preflight_failed", "storage_preflight_failed"],
  "clean_success": false,
  "error_message": "Steam import storage preflight failed for temp_dir: free space is below minimum.",
  "storage_budget": {
    "usage": {
      "downloaded_bytes": 0,
      "decompressed_bytes": 0,
      "stored_bytes": 0,
      "consumed_bytes": 0
    },
    "filesystems": {
      "upload_free_bytes": 19732590592,
      "temp_free_bytes": 1487069184,
      "same_filesystem": false
    }
  }
}
```

Parent terminal state is not running/null: yes.

Parent checkpoints observed: no. The job failed during storage preflight before entering the running/checkpointed phase. The terminal `result_json` is present and truthful, but this run did not exercise the D2 incremental checkpoint path.

## Child Jobs

No new `match_history_sync` child job was created for this run. Latest existing child jobs remained unchanged:

```text
id=16 status=succeeded
id=14 status=succeeded
id=12 status=succeeded
id=10 status=queued
id=9  status=succeeded
```

## Batch / Disk Guard

Batch cap observed: no. The run stopped before demo selection.

Disk guard observed: yes. The storage preflight blocked the run because `/tmp` free space was below configured minimum:

```text
temp_dir=/tmp
temp_free_bytes=1487069184
min_free_bytes=8589934592
```

No more than `STEAM_IMPORT_MAX_DEMOS_PER_RUN=1` demos were attempted/downloaded: yes, zero demos were attempted/downloaded.

Remaining pending demos stayed pending, not failed: not exercised; no Steam history rows changed.

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

Changed `matches` ids: none.

Changed `steam_history` ids: none.

Exact match date behavior: not exercised. No Steam metadata was fetched, no demos were downloaded or parsed, and no match date fields changed.

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

Journal since live start showed the single `POST /settings/imports/pull-all` returning `303`; no traceback, `500`, Steam download, node resolver, parser job or service crash was observed.

## Safety Summary

- Production DB touched: yes, job `#17` created/failed by the authorized one-button route.
- Production files deleted/moved: no.
- Live Steam/import/parser jobs run: one authorized one-button import was started; it stopped at storage preflight before Steam API, demo download or parser work.
- Demo downloads: no.
- Parser jobs: no.
- Schema changed: no.
- One-button clicked exactly once: yes.
- Commit made: no.

## Stale / Interrupted Behavior

Before live action, no `steam_import_all` job was running and job `#15` was `failed/interrupted`. The new job `#17` reached a terminal failed state immediately and did not become stale.

## Can v0.6 Be Promoted?

No.

The runtime safety guard worked and prevented an unsafe import, but this acceptance did not prove a successful/no-new/partial-success live import path. The current deployment has `/tmp` on a small tmpfs (`1.7G` total, about `1.4G` free), while the configured minimum free threshold is `8GiB`. Until temp storage is moved/resized or the storage guard configuration is intentionally revised, the one-button live import will fail preflight before Steam sync/download/parser work.

## Remaining Risks / Required Follow-Up

- Configure temp storage for Steam demo downloads on a filesystem with enough free space, preferably the same dedicated volume/bind mount strategy planned for uploads.
- Repeat live acceptance again after temp storage satisfies `STEAM_IMPORT_MIN_FREE_BYTES` and `STEAM_IMPORT_PRESERVE_FREE_BYTES`.
- This run did not exercise parent incremental checkpoints beyond terminal preflight result, demo batch cap, download streaming, parser integration or exact match-date persistence.
- Raw demo cleanup/offload remains a separate explicit operator/storage task; no cleanup was performed here.
