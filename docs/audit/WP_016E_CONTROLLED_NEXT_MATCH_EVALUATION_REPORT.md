# WP-016E Controlled Next-Match Evaluation Report

Date: 2026-07-04

## RESULT: FAILED

WP-016E attempted exactly one controlled next-match acquisition/evaluation path through the official guarded Steam import service function:

```python
from app.db.session import SessionLocal
from app.services.steam_integration import import_all_available_steam_matches

with SessionLocal() as db:
    result = import_all_available_steam_matches(db)
```

The attempt failed safely before sync/download/parser/evaluation work because storage preflight resolved the shell process temp directory to `/tmp`, which has less free space than `STEAM_IMPORT_MIN_FREE_BYTES`.

No new playable match was created. Recommendation `#5` still has zero evaluations. v0.8 cannot be promoted.

## Backup Path

```text
data/manual_backups/cs2_coach_before_wp016e_next_match_evaluation_20260704_211741.db
```

Backup SHA:

```text
45bd8b7b4a513cfa509ab40137abdc72b54820da2fe1244d44c42b495b4e374e  data/manual_backups/cs2_coach_before_wp016e_next_match_evaluation_20260704_211741.db
```

## DB SHA Before / After

Before:

```text
45bd8b7b4a513cfa509ab40137abdc72b54820da2fe1244d44c42b495b4e374e  data/cs2_coach.db
```

After:

```text
8b43c72703a2ea12da225a3c2ab6512df3e4b1079e468095b3327b6c55fb198c  data/cs2_coach.db
```

The DB changed only because the controlled attempt created `import_jobs.id=22` and persisted its failed `storage_preflight_failed` result.

## Exact Controlled Action Performed

One service-level equivalent of the guarded one-button Steam import was executed:

```bash
.venv/bin/python - <<'PY'
import json
from app.db.session import SessionLocal
from app.services.steam_integration import import_all_available_steam_matches

with SessionLocal() as db:
    result = import_all_available_steam_matches(db)
    print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
PY
```

Result:

```text
id=22
status=failed
overall_outcome=storage_preflight_failed
error=Steam import storage preflight failed for temp_dir: free space is below minimum.
```

Storage budget evidence from job `#22`:

```text
max_demos_per_run=1
max_bytes_per_job=2147483648
max_single_demo_bytes=629145600
upload_dir=/opt/jc-coach/data/uploads
temp_dir=/tmp
temp_free_bytes=1480065024
min_free_bytes=8589934592
```

The failure is environment-specific: direct shell invocation did not inherit the systemd `TMPDIR=/opt/jc-coach/data/tmp` used by the running service.

## Active Recommendation Before / After

Before and after the attempt:

```text
ACTIVE 5 survival active 70
needs_refresh=False
accepted_for_hard_progress=True
evaluations_checked=0
```

Recommendation `#5` remains valid and armed:

- category: `survival`;
- status: `active`;
- start_after_match_id: `70`;
- baseline ids: `[23,24,25,26,27,28,29,30,31,32,33,34,35,36,70]`;
- baseline source: all `demo`;
- health: accepted for hard progress.

## New Match ID If Created

None.

No playable match with `id > 70` exists after the attempt:

```text
MATCHES_AFTER_70 []
```

## New Match Source / Date / Artifact Validation

Not applicable. No new match was imported.

Post-attempt counts:

```text
matches=70
demo_matches=19
demo_parse_artifacts=19
```

## Recommendation #5 Evaluation Validation

No evaluation was created:

```text
EVAL_COUNT_5 0
```

No duplicate evaluation rows exist:

```text
DUPLICATE_EVALS []
```

Because no new match was created, there is no `evidence_json.metric_confidence` row to validate.

## Progress Update Validation

Progress did not update, truthfully:

```text
PROGRESS_5 recommendation_id=5 completed_matches=0 progress_score=0
summary=Ждём новые матчи после постановки цели.
needs_refresh=False
accepted_for_hard_progress=True
```

The loop remains armed but not exercised.

## Legacy Recommendation Safety

No new evaluations were created for legacy recommendations.

Existing state remains:

- old survival `#1`: archived, legacy, not active;
- active `grenades #3`: legacy/needs_refresh, not accepted for hard progress;
- active `map #4`: legacy/needs_refresh, not accepted for hard progress.

## Import / Parser / Job Evidence

Latest import job after the attempt:

```text
22 steam_import_all failed storage_preflight_failed
statuses=['storage_preflight_failed', 'storage_preflight_failed']
error=Steam import storage preflight failed for temp_dir: free space is below minimum.
```

No running import jobs:

```text
IMPORT_RUNNING 0
```

No parser job ran. No demo was downloaded.

## Storage Before / After

Before:

```text
3.6G data/uploads
4.0K data/tmp
28 .dem files
```

After:

```text
3.6G data/uploads
4.0K data/tmp
28 .dem files
```

No new files were found under `data/uploads` or `data/tmp` after the attempt timestamp.

## Service / Log Safety

Service restart after the attempt succeeded:

```text
Active: active (running)
Main PID: 143452 (uvicorn)
Application startup complete.
```

Unauthenticated GET smoke after restart returned expected redirects:

```text
/coach 303
/dashboard 303
/stats 303
/matches 303
/settings/imports 303
```

No traceback, HTTP 500, persistent report generation, parser/download process, or running import job was observed.

## Production Safety

- Production DB touched: yes, one failed `steam_import_all` job row was created.
- Production files touched: yes, DB backup and audit/docs files only.
- Production demo files touched: no.
- Live import/parser run: import path attempted; parser did not run.
- Demo downloaded: no.
- Persistent report generated: no.
- Schema changed: no.
- DB reset/resync performed: no.
- Commit made: no.

## Whether v0.8 Can Be Promoted

No.

The full recommendation loop has still not been proven because no post-refresh playable exact-date match was imported and no evaluation row was created for recommendation `#5`.

## Exact Blocker

The controlled service-level import attempt failed storage preflight before it could check/download a next match:

```text
temp_dir=/tmp
temp_free_bytes=1480065024
min_free_bytes=8589934592
status=storage_preflight_failed
```

Next attempt must use the authenticated/systemd app path, or run the service-level command with:

```bash
TMPDIR=/opt/jc-coach/data/tmp TEMP=/opt/jc-coach/data/tmp TMP=/opt/jc-coach/data/tmp
```

Do not rerun without a new explicit WP/authorization because WP-016E already consumed its one controlled attempt.

## Remaining Risks

- Recommendation `#5` remains armed with zero evaluations.
- Full `recommendation -> next match -> evaluation -> progress` acceptance remains pending.
- Legacy active `grenades #3` and `map #4` remain `needs_refresh`.
- Direct shell service-level import does not automatically inherit systemd TMPDIR; this must be controlled in the next authorized attempt.
