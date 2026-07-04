# WP-014D3 Operator Repair Stale Job #15 Report

Date: 2026-07-04

RESULT: REPAIRED

## Scope

Controlled operator DB repair for production `import_jobs.id=15` only. No live Steam/Valve import was run, no one-button import was clicked, no demos were downloaded, no parser jobs were started, no production demo files were deleted or moved, `data/uploads` was not cleaned, no schema change was made and no commit was made.

## Backup

Backup path:

```text
data/manual_backups/cs2_coach_before_wp014d3_repair_job15_20260704_183815.db
```

Backup SHA:

```text
8b0799d7da12230018a02a88031006f95e68cf7f3193d4b55d925ead5d3648b0  data/manual_backups/cs2_coach_before_wp014d3_repair_job15_20260704_183815.db
```

## DB SHA

Before repair:

```text
8b0799d7da12230018a02a88031006f95e68cf7f3193d4b55d925ead5d3648b0  data/cs2_coach.db
```

After repair:

```text
5a7aecf4cc0488c978c10eb7aecc5169aad0d277f52a15ec393fb0287b2a736e  data/cs2_coach.db
```

## Job #15 Before

```text
id: 15
provider: steam
job_type: steam_import_all
status: running
steam_account_id: None
created_at: 2026-07-04 14:23:51
started_at: 2026-07-04 14:23:51.453777
updated_at: <column absent>
finished_at: None
result_json: None
error_message: None
stale_by_configured_timeout: True
```

## Command Run

The intended exact repair command initially exposed a helper portability defect: `python3 scripts/...` did not load the app package/dependencies outside the project virtualenv. The helper was minimally repaired to add repo-root import path and re-exec through `.venv/bin/python` when invoked with system `python3`.

The repair command that succeeded was:

```bash
python3 scripts/repair_stale_steam_import_job.py --job-id 15 --i-have-backup --confirm-interrupt
```

Output:

```text
Marked steam_import_all ImportJob #15 interrupted.
```

## Job #15 After

```text
id: 15
provider: steam
job_type: steam_import_all
status: failed
steam_account_id: None
created_at: 2026-07-04 14:23:51
started_at: 2026-07-04 14:23:51.453777
updated_at: <column absent>
finished_at: 2026-07-04 15:39:01.101952
error_message: Operator marked stale steam_import_all job interrupted after WP-014C SIGKILL.
```

Persisted result:

```json
{
  "overall_outcome": "interrupted",
  "statuses": ["interrupted"],
  "status_summary": {"interrupted": 1},
  "clean_success": false,
  "error_message": "Operator marked stale steam_import_all job interrupted after WP-014C SIGKILL.",
  "interrupted_at": "2026-07-04T15:39:01.101918",
  "previous_overall_outcome": null,
  "progress": {
    "phase": "interrupted",
    "updated_at": "2026-07-04T15:39:01.101918",
    "recent_events": [
      {
        "phase": "interrupted",
        "at": "2026-07-04T15:39:01.101918",
        "reason": "Operator marked stale steam_import_all job interrupted after WP-014C SIGKILL."
      }
    ]
  }
}
```

## Import Job State

Before repair:

```text
job_type              status     count
match_history_sync    failed     1
match_history_sync    queued     1
match_history_sync    succeeded  5
steam_import_all      failed     1
steam_import_all      running    1
steam_import_all      succeeded  4
steam_openid_linked   queued     1
```

After repair:

```text
job_type              status     count
match_history_sync    failed     1
match_history_sync    queued     1
match_history_sync    succeeded  5
steam_import_all      failed     2
steam_import_all      succeeded  4
steam_openid_linked   queued     1
```

## Only Job #15 Changed

Backup/current comparison across all persisted `import_jobs` fields showed:

```text
changed_import_job_ids=[15]
only_job_15_changed=True
before_job_count=14
after_job_count=14
```

## Uploads / Production Files

Before repair:

```text
du -sh data/uploads: 3.1G
.dem count: 26
```

After repair:

```text
du -sh data/uploads: 3.1G
.dem count: 26
```

Production files deleted/moved: no.

## Runtime / Process Verification

No Steam helper, node demo resolver, demo download or parser process was running before or after repair. The only application process after repair was the existing uvicorn service:

```text
/opt/jc-coach/.venv/bin/python /opt/jc-coach/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010
```

`jc-coach.service` remained active. Journal tail showed repeated read-only `GET /settings/imports` requests and no `POST /settings/imports/pull-all`, live Steam import, download or parser activity during repair.

## Final Checks

```text
.venv/bin/ruff check .
All checks passed.

git diff --check
passed

python3 scripts/project_gate.py postflight
passed; DB SHA after repair is 5a7aecf4cc0488c978c10eb7aecc5169aad0d277f52a15ec393fb0287b2a736e
```

## Safety Summary

- Production DB touched: yes, exactly `import_jobs.id=15`.
- Production files deleted/moved: no.
- Live Steam/import/parser jobs run: no.
- Schema changed: no.
- One-button import clicked: no.
- `data/uploads` cleaned: no.
- Commit made: no.

## Remaining Risks

- The raw demo files retained during WP-014C remain on disk by policy; cleanup/offload still requires a separate explicit operator/storage WP.
- Repeat live acceptance still needs explicit authorization, DB SHA evidence, disk/batch guard settings and operator monitoring.
- There is still one old queued `match_history_sync` job (`id=10`); it was not in scope and was not mutated.

## Can WP-014C2 Repeat Live Acceptance Start?

Yes, from the stale-parent-job perspective. Job `#15` no longer blocks future one-button import queueing. Repeat live acceptance still requires a separate explicit WP authorization because it will run live Steam/import/download/parser work.
