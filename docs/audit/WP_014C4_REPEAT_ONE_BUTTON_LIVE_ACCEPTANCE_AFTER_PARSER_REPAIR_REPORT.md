# WP-014C4 Repeat One-Button Live Acceptance After Parser Repair

Date: 2026-07-04

## RESULT: PASS_WITH_WARNINGS

WP-014C4 repeated the real authenticated one-button Steam import after WP-014E. The run performed exactly one authorized `POST /settings/imports/pull-all`, downloaded/stored exactly one demo under the configured batch cap, imported it through the parser, preserved exact Steam date truth, and reached a terminal non-running parent job with bounded disk growth.

Warnings:

- `ImportJob.status` for parent job `#20` is `failed` because the current status enum has only `queued/running/succeeded/failed`; `result_json.overall_outcome` truthfully records `batch_cap_reached` with `success` and `exact_match_date_available`.
- The storage guard still reports `upload_dir_on_small_root_warning` because uploads and temp are on the root filesystem.
- Authenticated manual browser smoke was completed by the operator after the run.

## Backup Path

`data/manual_backups/cs2_coach_before_wp014c4_live_acceptance_20260704_191629.db`

## DB SHA Before/After

Before and backup:

```text
b8b98a3f79d31020dbb4e3c9bb9dba1a47d03371095dfc08fac87bf15010fda0  data/cs2_coach.db
b8b98a3f79d31020dbb4e3c9bb9dba1a47d03371095dfc08fac87bf15010fda0  data/manual_backups/cs2_coach_before_wp014c4_live_acceptance_20260704_191629.db
```

After:

```text
e801164c9370d1b4c98bb63cb77c78b026df23a5183f631d8dbafc862f5e391c  data/cs2_coach.db
```

The DB changed only through the explicitly authorized live one-button import flow.

## TMPDIR Verification

Systemd environment:

```text
Environment=PYTHONUNBUFFERED=1 TMPDIR=/opt/jc-coach/data/tmp TEMP=/opt/jc-coach/data/tmp TMP=/opt/jc-coach/data/tmp
```

Running process environment:

```text
PYTHONUNBUFFERED=1
TMPDIR=/opt/jc-coach/data/tmp
TEMP=/opt/jc-coach/data/tmp
TMP=/opt/jc-coach/data/tmp
```

Parent `result_json.storage_preflight.settings.temp_dir` also recorded `/opt/jc-coach/data/tmp`.

## Disk Before/After

Temp/root before:

```text
/opt/jc-coach/data/tmp: root filesystem, 38G size, 19G available, 50% used
/: 38G size, 19G available, 50% used
data/tmp: 4.0K
```

During run:

```text
data/tmp peaked in observed polling at 347M during decompression
root remained about 18G available, 51% used
```

After:

```text
/opt/jc-coach/data/tmp: root filesystem, 38G size, 18G available, 51% used
/: 38G size, 18G available, 51% used
data/tmp: 4.0K
```

## Uploads Before/After

Before:

```text
data/uploads: 3.4G
.dem count: 27
```

After:

```text
data/uploads: 3.6G
.dem count: 28
```

New retained demo:

```text
259882125 data/uploads/20260704161815_ae0c3ee138_CSGO-wBhTb-hHB9M-etd7p-iuwtR-XSUnB.dem
```

The file mtime is `2026-07-03 23:11:54 +0300`, inherited from the downloaded/decompressed demo; the filename prefix and DB evidence identify it as the WP-014C4 retained file.

## Exact Live Action Performed

The operator clicked the authenticated UI action exactly once. Journal evidence:

```text
Jul 04 19:17:44 jc uvicorn[128797]: "POST /settings/imports/pull-all HTTP/1.1" 303 See Other
```

No second `POST /settings/imports/pull-all` appeared in the monitored journal window.

## Parent Job

Parent job id: `20`

Before run: no `steam_import_all` job was running. Jobs `#15`, `#17` and `#18` were terminal failed states:

- `#15`: `failed/interrupted`;
- `#17`: `failed/storage_preflight_failed`;
- `#18`: failed from the WP-014C3 parser/model crash.

After run:

```text
id: 20
job_type: steam_import_all
status: failed
started_at: 2026-07-04 16:17:44.442871
finished_at: 2026-07-04 16:18:32.495341
error_message: Steam import outcome: batch_cap_reached
```

Result JSON summary:

```json
{
  "overall_outcome": "batch_cap_reached",
  "statuses": ["batch_cap_reached", "success", "exact_match_date_available"],
  "clean_success": false,
  "demo_download": {
    "processed": 1,
    "imported": 1,
    "failed": 0,
    "pending": 10,
    "remaining_pending": 10,
    "batch_cap_reached": true
  }
}
```

The parent job is terminal, non-running and has non-null truthful `result_json`.

## Child Jobs

Child job `#21`:

```text
job_type: match_history_sync
status: succeeded
sync_outcome: SUCCESS_NEW_MATCH_IMPORTED
collected: 10
inserted: 10
duplicates: 0
cursor_advanced: true
```

## Statuses Observed

- `batch_cap_reached`
- `success`
- `exact_match_date_available`

No `download_failed`, `parser_failed`, `storage_preflight_failed`, `disk_budget_exceeded`, traceback or HTTP 500 was observed.

## Storage Preflight

Storage preflight passed: yes.

Recorded paths:

```text
upload_dir=/opt/jc-coach/data/uploads
temp_dir=/opt/jc-coach/data/tmp
same_filesystem=true
```

Recorded guard settings:

```text
STEAM_IMPORT_MAX_DEMOS_PER_RUN=1
STEAM_IMPORT_MAX_BYTES_PER_JOB=2147483648
STEAM_IMPORT_MAX_SINGLE_DEMO_BYTES=629145600
STEAM_IMPORT_MIN_FREE_BYTES=8589934592
STEAM_IMPORT_PRESERVE_FREE_BYTES=5368709120
STEAM_IMPORT_UNKNOWN_DEMO_RESERVE_BYTES=1610612736
STEAM_IMPORT_STALE_RUNNING_JOB_SECONDS=3600
```

Recorded usage:

```json
{
  "downloaded_bytes": 152619560,
  "decompressed_bytes": 259882125,
  "stored_bytes": 259882125,
  "consumed_bytes": 672383810,
  "remaining_job_bytes": 1475099838
}
```

## Batch Cap

Batch cap observed: yes.

- Configured max demos per run: `1`.
- Attempted/imported demo results in parent JSON: `1`.
- Remaining pending after cap: `10`.
- Pending share-code rows remained pending and were not marked failed.

## Disk Guard

Disk guard observed: yes.

- Preflight passed with sufficient root/temp free space.
- Download/decompression/upload copy stayed under per-job budget.
- Temp dir returned to `4.0K` after completion.
- Disk did not approach `STEAM_IMPORT_PRESERVE_FREE_BYTES`.

## Parent Checkpoints

Parent checkpoints observed: yes.

Recent events included:

- `started`
- `account_checked`
- `share_codes_fetch_started`
- `share_codes_fetched`
- `demo_queued`
- `demo_downloading`
- `demo_downloaded`
- `demo_decompressing`
- `parser_started`
- `demo_stored`
- `parser_succeeded`
- `batch_cap_reached`

## Parser/Model Crash Fixed

Yes.

WP-014C3 failed when `played_at_source` was passed to `Match(...)`. WP-014C4 imported demo match `#70` successfully after WP-014E:

```text
source=demo
match_id=70
played_at=2026-07-03 19:34:35
map_name=de_overpass
demo_file=/opt/jc-coach/data/uploads/20260704161815_ae0c3ee138_CSGO-wBhTb-hHB9M-etd7p-iuwtR-XSUnB.dem
```

Parser artifact rows for match `#70` were persisted:

```text
demo_parse_artifacts=1
demo_rounds=21
demo_player_rounds=214
demo_weapon_stats=234
demo_damage_events=547
demo_duels=147
demo_grenade_events=198
```

## Matches Changed

Before:

```text
demo: 18
steam_history: 41
```

After:

```text
demo: 19
steam_history: 51
```

New imported demo match:

```text
matches.id=70
source=demo
external_match_id=8e214db9f747a573c7d30101ea294d5058a65035
```

New/updated Steam history row for imported demo:

```text
matches.id=69
source=steam_history
external_match_id=CSGO-wBhTb-hHB9M-etd7p-iuwtR-XSUnB
demo_file=/opt/jc-coach/data/uploads/20260704161815_ae0c3ee138_CSGO-wBhTb-hHB9M-etd7p-iuwtR-XSUnB.dem
```

## Exact Match Date Behavior

Exact date truth worked.

Parent result for the imported demo:

```json
{
  "played_at": "2026-07-03T19:34:35",
  "played_at_source": "steam_gc_match_time",
  "match_date_status": "exact_match_date_available",
  "match_date_source": "steam_gc_match_time"
}
```

`matches.raw_json` for demo match `#70` preserved:

```json
{
  "played_at": "2026-07-03T19:34:35",
  "played_at_source": "steam_gc_match_time",
  "match_date_status": "exact_match_date_available",
  "match_date_source": "steam_gc_match_time"
}
```

The Steam history placeholder row `#69` also retained the exact date metadata in `raw_json`. The playable demo match row `#70` has `Match.played_at=2026-07-03 19:34:35`.

## Service Health

Service remained active:

```text
Active: active (running)
Main PID: 128797 (uvicorn)
Memory after run: 1.1G, peak 2.1G
```

Journal scan since the live click found no traceback, exception, HTTP 500, CSRF rejection or rate limit event.

## Manual Browser Smoke

Requested pages:

- `/settings/imports`
- `/matches`
- `/coach`
- `/dashboard`
- `/upload`

Operator status: completed after the run; the operator reported that everything is ready. No repeat import click was requested or performed. Pre-click and in-run journal also showed authenticated `GET` 200 responses for several of these pages.

## Production Safety

- Production DB touched: yes, by the explicitly authorized one-button live import.
- Production files deleted/moved: no.
- Live Steam/import/parser jobs run: yes, exactly as part of the single authorized one-button import.
- Separate parser jobs run: no.
- Exact share-code import run: no.
- Manual upload run: no.
- One-button clicked exactly once: yes, by operator confirmation and journal evidence.
- Schema changed: no.
- Commit made: no.

## Whether v0.6 Can Be Promoted

Yes, for controlled personal `v0.6` import acceptance, with warnings:

- The primary one-button path is now bounded by storage guard/batch cap.
- Parent checkpoints and terminal `result_json` are durable and truthful.
- Parser/import no longer crashes on `played_at_source`.
- Exact date truth is explicit and exact when Steam GC `match_time` is available.
- Service stayed healthy and disk growth was bounded.

Promotion should still document that `ImportJob.status` uses `failed` for non-clean terminal outcomes such as `batch_cap_reached`, with the canonical truth in `result_json`.

## Remaining Risks

- Raw demos are still retained by policy (`retain_raw_for_parser_development`), so storage growth remains bounded per run but not eliminated.
- Uploads/temp still live on the root filesystem; a dedicated volume or mount remains the safer deployment shape.
- Import status enum remains coarse; `result_json` carries the truthful outcome taxonomy.
- Manual authenticated browser smoke was operator-confirmed; detailed page screenshots were not captured.
- Friends/public readiness remains blocked by broader security, ownership, migration, backup and observability gates.
