# WP-017B Controlled Bulk Import Plan / Settings Report

Date: 2026-07-04

## RESULT: PLANNED

WP-017B defines the operator runbook for the first `v0.9` controlled import batch.

This was planning/runbook only. No runtime code, tests, schema, production DB data, live Steam/Valve import, demo download, parser job, app persistent report, DB reset/resync, commit or production demo file lifecycle action was changed or run.

## Product Version Observed

`v0.8`

Target version remains `v0.9` Real Data Onboarding / Bulk Demo Usage.

Accepted starting loop:

```text
recommendation #5 -> real exact-date match #72 -> evaluation #76 -> completed_matches=1
```

## DB SHA

```text
36ccd84dc5c695af1c75a74f8d1059ade68a2a0355bb43aca1a7b473dd68f320  data/cs2_coach.db
```

## Current Capacity Snapshot

Initial read-only snapshot:

| Item | Value |
|---|---:|
| latest commit | `05e19e6 Diagnose real data onboarding` |
| git status | clean |
| root filesystem | `38G` total, `19G` used, `18G` available, `52%` used |
| root available bytes | `18,326,024,192` bytes / `17.07 GiB` |
| `/tmp` available bytes | `1,403,219,968` bytes / `1.31 GiB` |
| `data/uploads` | `3.8G`; `4,062,565,189` bytes |
| `data/tmp` | `4.0K`; `0` bytes by `du -sb` |
| `data/manual_backups` | `1.2G`; `1,201,012,736` bytes |
| upload demo files | `29` |
| upload demo bytes | `4,062,565,188` bytes |
| service | `jc-coach.service` active/running, PID `146750`, memory about `66.2M` |
| systemd temp env | `TMPDIR=/opt/jc-coach/data/tmp`, `TEMP=/opt/jc-coach/data/tmp`, `TMP=/opt/jc-coach/data/tmp` |

Current data facts from WP-017A and read-only DB checks:

| Item | Value |
|---|---:|
| total matches | `72` |
| playable demo matches | `20` |
| steam_history placeholders | `52` |
| demo parse artifact rows | `20` |
| active accepted recommendation | `#5` survival |
| recommendation `#5` evaluations | `1` green evaluation |
| queued/running `steam_import_all` jobs | none |
| latest parent import job | `#25 steam_import_all`, `succeeded`, `overall_outcome=success` |
| latest child sync job | `#26 match_history_sync`, `succeeded`, `sync_outcome=SUCCESS_NEW_MATCH_IMPORTED` |

## Import Settings To Keep

Do not raise import caps in WP-017C.

| Setting | Keep value |
|---|---:|
| `STEAM_IMPORT_MAX_DEMOS_PER_RUN` | `1` |
| `STEAM_IMPORT_MAX_BYTES_PER_JOB` | `2,147,483,648` bytes / `2.00 GiB` |
| `STEAM_IMPORT_MAX_SINGLE_DEMO_BYTES` | `629,145,600` bytes / `600 MiB` |
| `STEAM_IMPORT_MIN_FREE_BYTES` | `8,589,934,592` bytes / `8.00 GiB` |
| `STEAM_IMPORT_PRESERVE_FREE_BYTES` | `5,368,709,120` bytes / `5.00 GiB` |
| `STEAM_IMPORT_UNKNOWN_DEMO_RESERVE_BYTES` | `1,610,612,736` bytes / `1.50 GiB` |
| stale running parent timeout | `3,600` seconds |
| startup stale repair | disabled |

First batch strategy:

1. Keep `STEAM_IMPORT_MAX_DEMOS_PER_RUN=1`.
2. Plan at most `3` one-demo runs.
3. Stop after every run for inspection.
4. Stop immediately on parser, storage, recommendation, service/runtime or unexpected DB/file anomaly.
5. Do not raise the cap to `2` or `3` in WP-017C.

## Launch Method

Preferred method: authenticated/systemd app path.

Operator action:

1. Sign in as the owner.
2. Open `/settings/imports`.
3. Confirm Steam account is linked and has Game Authentication Code plus latest share-code cursor.
4. Confirm the import overview shows no active `steam_import_all` job.
5. Click the one-button import action exactly once: `POST /settings/imports/pull-all`.
6. Wait until the parent `steam_import_all` job reaches a terminal state before any second action.

Expected route behavior:

- `POST /settings/imports/pull-all` calls `queue_steam_import_all(db)`.
- A parent `steam_import_all` job is created or reused if already queued/running.
- If newly queued, the web route schedules `_run_steam_import_all_background(job.id)`.
- The parent syncs share codes through a child `match_history_sync` job, then runs demo download/parser/import with `limit=max(1, STEAM_IMPORT_MAX_DEMOS_PER_RUN)`.
- Download is clamped again by `storage_budget.settings.max_demos_per_run`.

Do not use exact-share-code manual import for WP-017C unless a later WP explicitly changes scope. The target is controlled one-button real data onboarding.

## Shell TMPDIR Requirement

Shell fallback is allowed only if the authenticated UI path is unavailable and WP-017C explicitly authorizes live import/parser/download/DB mutation.

The shell fallback must set all temp variables:

```bash
cd /opt/jc-coach
TMPDIR=/opt/jc-coach/data/tmp \
TEMP=/opt/jc-coach/data/tmp \
TMP=/opt/jc-coach/data/tmp \
.venv/bin/python - <<'PY'
import json
from app.db.session import SessionLocal
from app.services.steam_integration import import_all_available_steam_matches

with SessionLocal() as db:
    result = import_all_available_steam_matches(db)
    print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
PY
```

Rules for shell fallback:

- one command execution equals one WP-017C run;
- do not wrap it in a retry loop;
- do not run a second attempt until the post-run checklist is complete;
- if it creates or finds a running parent job, inspect the job before deciding anything;
- if temp resolves to anything other than `/opt/jc-coach/data/tmp`, stop.

## Pre-Run Checklist

Run this checklist before every WP-017C attempt.

Repository and gates:

```bash
git status --short
git log --oneline -15
python3 scripts/project_gate.py preflight
python3 scripts/project_gate.py changed
python3 scripts/project_gate.py required-checks
```

DB and backup evidence:

```bash
sha256sum data/cs2_coach.db
```

Before the first WP-017C live run, create exactly one DB backup using the backup policy below.

Storage:

```bash
df -h
df -B1 / /tmp /opt/jc-coach/data/uploads /opt/jc-coach/data/tmp
du -sh data/uploads data/tmp data/manual_backups 2>/dev/null || true
du -sb data/uploads data/tmp data/manual_backups 2>/dev/null || true
find data/uploads -maxdepth 1 -type f \( -name "*.dem" -o -name "*.dem.bz2" \) | wc -l
find data/uploads -maxdepth 1 -type f \( -name "*.dem" -o -name "*.dem.bz2" \) -printf "%s\n" | awk '{sum+=$1; count+=1} END {print count, sum}'
```

Hard pre-run disk gate:

- root free must be at least `12 GiB`;
- `data/tmp` must be empty or only trivial filesystem overhead;
- do not start a run if `data/tmp` contains retained large files.

Service:

```bash
systemctl status jc-coach --no-pager
systemctl show jc-coach -p Environment
```

DB read-only state:

```bash
.venv/bin/python - <<'PY'
import sqlite3
from pathlib import Path

uri = f"file:{Path('data/cs2_coach.db').resolve()}?mode=ro"
conn = sqlite3.connect(uri, uri=True)
conn.row_factory = sqlite3.Row

queries = {
    "queued_running_parent_jobs": """
        SELECT id, job_type, status, created_at, started_at
        FROM import_jobs
        WHERE provider='steam'
          AND job_type='steam_import_all'
          AND status IN ('queued', 'running')
        ORDER BY id
    """,
    "latest_import_jobs": """
        SELECT id, job_type, status, created_at, started_at, finished_at,
               substr(coalesce(result_json, ''), 1, 500) AS result_head
        FROM import_jobs
        WHERE provider='steam'
        ORDER BY id DESC
        LIMIT 8
    """,
    "recommendation_state": """
        SELECT id, category, status, target_period_matches, start_after_match_id
        FROM coach_recommendations
        ORDER BY id
    """,
    "evaluation_counts": """
        SELECT recommendation_id, count(*) AS evaluations
        FROM match_recommendation_evaluations
        GROUP BY recommendation_id
        ORDER BY recommendation_id
    """,
}

for label, sql in queries.items():
    print(f"## {label}")
    rows = conn.execute(sql).fetchall()
    if not rows:
        print("(none)")
    for row in rows:
        print(dict(row))
PY
```

Required pre-run state:

- git status is clean except explicitly planned documentation changes;
- DB SHA is recorded;
- backup exists before the first live WP-017C run;
- service is active/running;
- systemd env includes `TMPDIR/TEMP/TMP=/opt/jc-coach/data/tmp`;
- no queued/running parent `steam_import_all` job exists;
- latest jobs are understood;
- recommendation `#5` is active, accepted and has current evaluation count recorded;
- legacy recommendations `#3/#4` evaluation counts are recorded before the run.

## Backup Policy

Backup is required before the first WP-017C live run.

Recommended command:

```bash
cd /opt/jc-coach
ts=$(date +%Y%m%d_%H%M%S)
backup="data/manual_backups/cs2_coach_before_wp017c_first_batch_${ts}.db"
cp --reflink=auto data/cs2_coach.db "$backup"
sha256sum data/cs2_coach.db "$backup"
du -sh data/manual_backups
```

Policy:

- create one backup before the first WP-017C run;
- record DB SHA before and after every run;
- do not create unlimited backups without `data/manual_backups` accounting;
- if a later WP proposes raising `STEAM_IMPORT_MAX_DEMOS_PER_RUN`, require a fresh backup before that cap change or run.

## Run Steps

Each run is one controlled attempt.

1. Complete the pre-run checklist.
2. Confirm root free is at least `12 GiB`.
3. Confirm no queued/running parent `steam_import_all` exists.
4. Launch either the authenticated UI action or the one-attempt shell fallback.
5. Record parent job id immediately.
6. Wait for the parent job to become terminal: `succeeded` or `failed`.
7. Do not start a second run in the same session until the post-run checklist is complete.
8. Stop after `3` terminal attempts maximum, even if all look healthy.

Expected WP-017C shape:

- Run 1: one attempt, inspect fully.
- Run 2: allowed only if Run 1 is terminal, understood and safe.
- Run 3: allowed only if Run 2 is terminal, understood and safe.
- After Run 3, stop and proceed to WP-017D.

## Post-Run Checklist

Run after every terminal attempt.

Storage and service:

```bash
sha256sum data/cs2_coach.db
df -h
df -B1 / /tmp /opt/jc-coach/data/uploads /opt/jc-coach/data/tmp
du -sh data/uploads data/tmp data/manual_backups 2>/dev/null || true
du -sb data/uploads data/tmp data/manual_backups 2>/dev/null || true
find data/uploads -maxdepth 1 -type f \( -name "*.dem" -o -name "*.dem.bz2" \) | wc -l
systemctl status jc-coach --no-pager
```

Job and recommendation inspection:

```bash
.venv/bin/python - <<'PY'
import json
import sqlite3
from pathlib import Path

uri = f"file:{Path('data/cs2_coach.db').resolve()}?mode=ro"
conn = sqlite3.connect(uri, uri=True)
conn.row_factory = sqlite3.Row

for label, sql in {
    "latest_import_jobs": """
        SELECT id, job_type, status, created_at, started_at, finished_at,
               result_json, error_message
        FROM import_jobs
        WHERE provider='steam'
        ORDER BY id DESC
        LIMIT 6
    """,
    "latest_demo_matches": """
        SELECT id, source, map_name, played_at, demo_file,
               substr(coalesce(raw_json, ''), 1, 1200) AS raw_head
        FROM matches
        WHERE source='demo'
        ORDER BY id DESC
        LIMIT 6
    """,
    "latest_artifacts": """
        SELECT match_id, created_at, parser_version
        FROM demo_parse_artifacts
        ORDER BY match_id DESC
        LIMIT 6
    """,
    "recommendation_evaluations": """
        SELECT id, recommendation_id, match_id, status, score,
               substr(coalesce(evidence_json, ''), 1, 800) AS evidence_head
        FROM match_recommendation_evaluations
        ORDER BY id DESC
        LIMIT 12
    """,
}.items():
    print(f"## {label}")
    for row in conn.execute(sql):
        item = dict(row)
        if item.get("result_json"):
            try:
                parsed = json.loads(item["result_json"])
                item["result_json"] = {
                    "overall_outcome": parsed.get("overall_outcome"),
                    "statuses": parsed.get("statuses"),
                    "clean_success": parsed.get("clean_success"),
                    "demo_download": parsed.get("demo_download"),
                    "sync_jobs": parsed.get("sync_jobs"),
                }
            except Exception:
                pass
        print(item)
PY
```

Required post-run facts to record:

- parent `steam_import_all` job id, status, `overall_outcome`, `statuses`, `clean_success` and `error_message`;
- child `match_history_sync` job id, status and `sync_outcome`;
- new share code if any;
- new playable demo match id if any;
- map;
- exact date truth: `match_date_status=exact_match_date_available` and `match_date_source=steam_gc_match_time` for hard recommendation progress;
- parser artifact row exists for a new playable demo match;
- retained demo file path exists and size is recorded;
- `data/uploads` delta;
- `data/tmp` cleanup;
- recommendation `#5` evaluation is created exactly once if a new exact playable post-refresh match exists;
- recommendation `#5.completed_matches` increments by one for each accepted exact playable evaluation;
- legacy recommendations `#3/#4` receive no new evaluations;
- no traceback, HTTP 500, hung service or stale running import job;
- service remains active/running.

## Outcome Taxonomy

Use `ImportJob.result_json` as the canonical source of truth. Coarse `ImportJob.status` may be `failed` for non-clean but bounded outcomes.

| Outcome | Classification | Criteria |
|---|---|---|
| `PASS_ONE_DEMO_IMPORTED_AND_EVALUATED` | pass | Exactly one new playable `demo` match was imported, exact date came from `steam_gc_match_time`, parser artifacts exist, recommendation `#5` got exactly one new evaluation with `metric_confidence`, progress incremented, service/storage are healthy. |
| `PASS_NO_NEW_MATCH` | pass | Parent is terminal with `overall_outcome=no_new`; no demo download/parser/evaluation occurred; service/storage remain healthy. |
| `PASS_DUPLICATE_SKIPPED` | pass | Parent/child result shows duplicate-only or demo duplicate skipped; no duplicate playable match/evaluation was created; service/storage remain healthy. |
| `WARNING_BATCH_CAP_REACHED` | warning | `result_json.statuses` includes `batch_cap_reached`. This is expected with cap `1` when more pending fresh demos exist. It is acceptable only if the one attempted demo outcome is otherwise understood and post-run checks pass. Stop for inspection before any next run. |
| `FAILED_STORAGE_GUARD` | fail | `storage_preflight_failed`, `disk_budget_exceeded` or `demo_too_large` appears, or root/data/tmp state violates stop conditions. |
| `FAILED_PARSER` | fail | `parser_failed`, retained raw demo after parser failure, missing parser artifacts for an imported playable match, or parser traceback. |
| `FAILED_IMPORT_JOB_STALE` | fail | Parent job remains queued/running beyond expected runtime, exceeds stale threshold, or stops updating progress. |
| `FAILED_RECOMMENDATION_EVALUATION_MISSING` | fail | A new exact playable post-refresh match exists but recommendation `#5` did not receive exactly one evaluation with `metric_confidence`. |
| `FAILED_SERVICE_RUNTIME` | fail | Service inactive, traceback/500, hung shutdown/restart, page builder unavailable or severe slowdown after run. |

## Stop Conditions

Hard stop before a run:

- root free is below `12 GiB`;
- `data/tmp` contains retained large files;
- a queued/running `steam_import_all` job exists;
- service is not active/running;
- systemd temp env is missing or not pinned to `/opt/jc-coach/data/tmp`;
- git status has unexplained changes.

Hard stop after a run:

- root free is below `10 GiB`;
- `data/tmp` retains large files after job completion;
- storage guard reports `storage_preflight_failed`, `disk_budget_exceeded` or `demo_too_large`;
- parser fails or parser artifacts are missing for a new imported demo;
- service logs show traceback/500 or service becomes unavailable;
- parent import job is stuck running or lacks truthful terminal `result_json`;
- recommendation `#5` does not evaluate a new exact playable match;
- legacy recommendations `#3/#4` receive new evaluations;
- `/coach`, `/stats`, `/dashboard`, `/matches` become slow or unavailable under owner session;
- any unexplained DB/file/storage delta appears.

Soft stop and inspect:

- `batch_cap_reached` appears;
- no-new or duplicate outcomes repeat and cursor freshness is unclear;
- service memory materially grows and does not return near baseline;
- one attempt takes roughly more than `3` minutes without an understood Valve/network reason;
- progress wording becomes misleading after added evaluations.

## WP-017C Authorization Requirements

WP-017C may proceed only with an explicit user prompt authorizing live Steam/Valve import, demo download, parser job and production DB mutation.

The WP-017C prompt should state:

- exactly which launch method is authorized: authenticated UI path or shell fallback;
- max attempts: at most `3`;
- cap remains `STEAM_IMPORT_MAX_DEMOS_PER_RUN=1`;
- backup is required before the first run;
- stop after every run for inspection;
- no cap raise;
- no raw demo delete/move/compress;
- no schema change;
- no persistent app report generation;
- no commit unless explicitly requested.

## WP-017D Acceptance Gate

WP-017D should run after at most `3` successful/terminal one-demo attempts, or earlier if any anomaly occurs.

WP-017D must inspect:

- data integrity and DB SHA before/after;
- parent and child import job truth;
- parser artifact coverage for new playable demos;
- exact-date coverage and date-source truth;
- recommendation `#5` progress and evaluation evidence;
- absence of new legacy `#3/#4` evaluations;
- `/coach`, `/stats`, `/dashboard`, `/matches` authenticated runtime performance;
- storage growth versus estimate;
- `data/tmp` cleanup;
- retained raw demo paths and sizes;
- match mode unknown labeling risk;
- whether a later WP may safely consider cap `2`.

Do not raise cap in WP-017D itself unless a later explicit repair/settings WP authorizes that change.

## Match Mode Handling

Match mode repair should not block the first small WP-017C batch.

Policy for WP-017C:

- keep mode as `unknown`;
- do not claim Premier, Competitive or Wingman from map name;
- do not claim match `#72` or future imports are Competitive in UI/report unless persisted data proves it;
- record any new stored metadata that might help future mode recovery;
- schedule WP-017E Match Mode Classification Repair if recoverable.

## Production Safety

- Production DB touched: no.
- Production files touched: no production demo/upload/temp files touched; repository documentation files changed only.
- Live import/parser run: no.
- Live Steam/Valve import run: no.
- Demo downloaded: no.
- Parser job run: no.
- App persistent report generated: no.
- Runtime code changed: no.
- Tests changed: no.
- Schema changed: no.
- Commit made: no.

## Can Proceed To WP-017C

Yes, with explicit live-run authorization.

WP-017C should execute the first controlled real-data batch using this runbook, keep cap `1`, run at most `3` one-demo attempts, and stop after each attempt for inspection.
