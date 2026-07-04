# WP-016E2 Controlled Next-Match Evaluation Retry Report

Date: 2026-07-04

## RESULT: BLOCKED_NO_NEW_MATCH

WP-016E2 retried the controlled next-match acquisition/evaluation path exactly once through the official guarded Steam import service function, this time with explicit shell temp environment:

```bash
TMPDIR=/opt/jc-coach/data/tmp TEMP=/opt/jc-coach/data/tmp TMP=/opt/jc-coach/data/tmp .venv/bin/python - <<'PY'
import json
from app.db.session import SessionLocal
from app.services.steam_integration import import_all_available_steam_matches

with SessionLocal() as db:
    result = import_all_available_steam_matches(db)
    print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
PY
```

The TMPDIR issue from WP-016E was fixed for this service-level invocation. Storage preflight used `/opt/jc-coach/data/tmp`, passed, and the run reached a truthful terminal `no_new` outcome.

No new playable exact-date match exists after recommendation `#5.start_after_match_id=70`, so no demo was downloaded, no parser ran, and no recommendation evaluation was created. v0.8 cannot be promoted yet because the full next-match evaluation leg remains unexercised.

## Backup Path

```text
data/manual_backups/cs2_coach_before_wp016e2_next_match_evaluation_retry_20260704_212234.db
```

Backup SHA:

```text
8b43c72703a2ea12da225a3c2ab6512df3e4b1079e468095b3327b6c55fb198c  data/manual_backups/cs2_coach_before_wp016e2_next_match_evaluation_retry_20260704_212234.db
```

## DB SHA Before / After

Before:

```text
8b43c72703a2ea12da225a3c2ab6512df3e4b1079e468095b3327b6c55fb198c  data/cs2_coach.db
```

After:

```text
7f32ffc71773a3786bac5900a0064e5030ac99e50eb2eb96967273f8eb126854  data/cs2_coach.db
```

The DB changed only because the controlled import attempt persisted `import_jobs.id=23` and child `import_jobs.id=24`.

## TMPDIR / Environment Evidence

Systemd service environment before the attempt:

```text
Environment=PYTHONUNBUFFERED=1 TMPDIR=/opt/jc-coach/data/tmp TEMP=/opt/jc-coach/data/tmp TMP=/opt/jc-coach/data/tmp
```

Shell command environment used for the attempt:

```text
TMPDIR=/opt/jc-coach/data/tmp
TEMP=/opt/jc-coach/data/tmp
TMP=/opt/jc-coach/data/tmp
```

Storage guard evidence from job `#23`:

```text
upload_dir=/opt/jc-coach/data/uploads
temp_dir=/opt/jc-coach/data/tmp
upload_temp_same_filesystem=true
free_bytes_before_preflight=18737889280
min_free_bytes=8589934592
preserve_free_bytes=5368709120
max_demos_per_run=1
max_bytes_per_job=2147483648
max_single_demo_bytes=629145600
```

## Import Job ID / Status / Result

Parent job:

```text
id=23
job_type=steam_import_all
status=succeeded
overall_outcome=no_new
statuses=["no_new", "exact_match_date_unavailable"]
```

Child job:

```text
id=24
job_type=match_history_sync
status=succeeded
sync_outcome=SUCCESS_NO_NEW_MATCHES
collected=0
inserted=0
duplicates=0
cursor_advanced=false
```

Demo phase:

```text
pending_demo_download=0
processed=0
imported=0
failed=0
remaining_pending=0
```

No retry was performed after the `no_new` result.

## Active Recommendation Before / After

Before and after:

```text
ACTIVE 5 survival active start_after_match_id=70
needs_refresh=false
accepted_for_hard_progress=true
evaluations_checked=0
```

Recommendation `#5` remains valid and armed:

- category: `survival`;
- status: `active`;
- baseline ids: `[23,24,25,26,27,28,29,30,31,32,33,34,35,36,70]`;
- baseline source: all `demo`;
- health: accepted for hard progress.

## New Match ID If Created

None.

Post-run check:

```text
MATCHES_AFTER_70 []
```

## New Match Source / Date / Artifact Validation

Not applicable. No new playable match was imported.

Post-run counts:

```text
matches=70
playable_demo_matches=19
demo_parse_artifacts=19
```

## Recommendation #5 Evaluation Validation

No evaluation was created because no new match was created:

```text
EVAL_COUNT_5 0
```

No duplicate evaluation rows exist:

```text
DUPLICATE_EVALS []
```

There is no new `evidence_json.metric_confidence` row to validate until a post-refresh match exists.

## Progress Update Validation

Progress remains truthfully waiting:

```text
completed_matches=0
summary=Ждём новые матчи после постановки цели.
needs_refresh=false
accepted_for_hard_progress=true
```

## Legacy Recommendation Safety

No evaluations were created for legacy recommendations.

Expected state remains:

- old survival `#1`: archived, not selected as active;
- active `grenades #3`: legacy/needs_refresh, not accepted for hard progress;
- active `map #4`: legacy/needs_refresh, not accepted for hard progress.

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
Application startup complete.
```

Unauthenticated GET smoke returned expected login redirects; no authenticated session was available to Codex and auth was not bypassed:

```text
/coach 303 -> /login
/dashboard 303 -> /login
/stats 303 -> /login
/matches 303 -> /login
/settings/imports 303 -> /login
```

Journal after the attempt/restart showed clean shutdown/startup and no traceback/500 evidence.

## Production Safety

- production DB touched: yes, controlled backup plus import job rows `#23` and `#24`;
- production demo/upload files deleted or moved: no;
- production files touched: yes, DB backup and docs/report only;
- live import/parser run: guarded Steam import/sync attempt yes; demo download no; parser no;
- persistent report generated: no;
- schema changed: no;
- full reset/resync performed: no;
- bulk import performed: no;
- batch cap raised: no.

## Whether v0.8 Can Be Promoted

No.

Exact blocker: recommendation `#5` is still armed, but there is no real post-refresh playable exact-date match after `start_after_match_id=70`. The full loop `recommendation #5 -> next match -> evaluation with metric_confidence -> progress update` has not yet been exercised.

## Remaining Risks

- v0.8 promotion still requires one real post-refresh playable exact-date match and a resulting evaluation for recommendation `#5`.
- Future service-level import attempts must keep explicit `TMPDIR/TEMP/TMP=/opt/jc-coach/data/tmp` unless performed through the authenticated/systemd app path.
- Legacy active categories `grenades #3` and `map #4` remain needs-refresh and are not accepted for hard progress.
- `data/uploads` and `data/tmp` still live on the root filesystem; storage guards bounded this attempt, but dedicated storage remains recommended.
