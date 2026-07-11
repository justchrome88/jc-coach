# WP-016E3 Controlled Competitive Dust2 Evaluation Report

Date: 2026-07-04

## RESULT: FAILED

WP-016E3 performed exactly one controlled Steam import/parser/evaluation attempt through the official guarded Steam import service path with explicit temp environment:

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

The import/storage/parser part succeeded. The expected new Competitive Dust2 match was imported as playable exact-date demo match `#72`.

The recommendation loop did not complete: recommendation `#5` still has zero evaluations after the import, and progress still reports waiting for new matches. v0.8 cannot be promoted.

## Backup Path

```text
data/manual_backups/cs2_coach_before_wp016e3_competitive_dust2_evaluation_20260704_220830.db
```

Backup SHA:

```text
7f32ffc71773a3786bac5900a0064e5030ac99e50eb2eb96967273f8eb126854  data/manual_backups/cs2_coach_before_wp016e3_competitive_dust2_evaluation_20260704_220830.db
```

## DB SHA Before / After

Before:

```text
7f32ffc71773a3786bac5900a0064e5030ac99e50eb2eb96967273f8eb126854  data/cs2_coach.db
```

After:

```text
5d33469b7f4e5eff27354f04c635a8f6400a667b43858ed3716da4e0b6d0c696  data/cs2_coach.db
```

The DB changed because the authorized import created Steam/import jobs, one `steam_history` placeholder row, one playable demo match row and parser artifacts.

## TMPDIR / Environment Evidence

Systemd service environment:

```text
Environment=PYTHONUNBUFFERED=1 TMPDIR=/opt/jc-coach/data/tmp TEMP=/opt/jc-coach/data/tmp TMP=/opt/jc-coach/data/tmp
```

The shell command explicitly set:

```text
TMPDIR=/opt/jc-coach/data/tmp
TEMP=/opt/jc-coach/data/tmp
TMP=/opt/jc-coach/data/tmp
```

Storage guard evidence:

```text
upload_dir=/opt/jc-coach/data/uploads
temp_dir=/opt/jc-coach/data/tmp
same_filesystem=true
max_demos_per_run=1
max_bytes_per_job=2147483648
max_single_demo_bytes=629145600
downloaded_bytes=144862751
decompressed_bytes=244346590
stored_bytes=244346590
remaining_job_bytes=1513927717
warnings=["upload_dir_on_small_root_warning"]
```

## Import Job ID / Status / Result

Parent:

```text
id=25
job_type=steam_import_all
status=succeeded
overall_outcome=success
statuses=["success", "exact_match_date_available"]
```

Child sync:

```text
id=26
job_type=match_history_sync
status=succeeded
sync_outcome=SUCCESS_NEW_MATCH_IMPORTED
collected=1
inserted=1
cursor_advanced=true
share_code=CSGO-DearK-t4hWu-OUquu-aoKwy-KhMMB
```

Demo phase:

```text
processed=1
imported=1
failed=0
batch_cap_reached=false
remaining_pending=0
```

## Active Recommendation Before / After

Before:

```text
recommendation_id=5
category=survival
status=active
start_after_match_id=70
needs_refresh=false
accepted_for_hard_progress=true
evaluation_count=0
```

After:

```text
recommendation_id=5
category=survival
status=active
start_after_match_id=70
needs_refresh=false
accepted_for_hard_progress=true
evaluation_count=0
```

Recommendation `#5` remains healthy and accepted for hard progress, but it did not receive an evaluation for match `#72`.

## New Match ID

The controlled import created:

```text
steam_history placeholder match_id=71
playable demo match_id=72
share_code=CSGO-DearK-t4hWu-OUquu-aoKwy-KhMMB
```

## Expected Map Dust2 Validation

Match `#72`:

```text
map_name=de_dust2
```

This matches the expected Dust2 / `de_dust2` Competitive match.

## New Match Source / Date / Artifact Validation

Match `#72`:

```text
source=demo
external_match_id=f7590c9aa156bf791e651d0fdd3cdc817188f834
played_at=2026-07-04 15:31:49
exact=true
match_date_status=exact_match_date_available
match_date_source=steam_gc_match_time
played_at_source=steam_gc_match_time
```

Retained demo:

```text
data/uploads/20260704190858_5c1b0e8aac_CSGO-DearK-t4hWu-OUquu-aoKwy-KhMMB.dem
size=244346590 bytes
```

Parser artifacts for match `#72`:

```text
parse_artifacts=1
rounds=21
player_rounds=198
weapon_stats=258
damage_events=499
duels=137
grenades=240
```

## Recommendation #5 Evaluation Validation

Failed.

Post-import evidence:

```text
EVAL_COUNT_5=0
EVAL_COUNTS_BY_REC=[(1, 19), (2, 18), (3, 19), (4, 19)]
DUPLICATE_EVALS=[]
```

No evaluation row exists for recommendation `#5` and match `#72`; therefore no `evidence_json.metric_confidence` could be validated.

The code path still contains a parser-side call to `evaluate_new_matches(db)` after saving parser artifacts, and `evaluate_new_matches()` would skip only recommendations that need refresh or matches at/before `start_after_match_id`. Read-only inspection showed `_ordered_matches(db)` includes match `#72`, and recommendation `#5` is not `needs_refresh`. The observed runtime outcome therefore indicates a post-import evaluation trigger defect that needs focused repair.

## Progress Update Validation

Failed.

Progress remained:

```text
completed_matches=0
summary=Ждём новые матчи после постановки цели.
needs_refresh=false
accepted_for_hard_progress=true
```

## Legacy Recommendation Safety

Legacy recommendations stayed isolated:

- old survival `#1`: archived, legacy, not active;
- active `grenades #3`: legacy/needs_refresh, not accepted for hard progress;
- active `map #4`: legacy/needs_refresh, not accepted for hard progress.

No new evaluations were created for legacy recommendations.

## Storage Before / After

Before:

```text
3.6G data/uploads
4.0K data/tmp
28 .dem files
```

After:

```text
3.8G data/uploads
4.0K data/tmp
29 .dem files
```

The only new retained demo observed was:

```text
data/uploads/20260704190858_5c1b0e8aac_CSGO-DearK-t4hWu-OUquu-aoKwy-KhMMB.dem
```

## Service / Log Safety

Service restart after the attempt succeeded:

```text
Active: active (running)
Application startup complete.
```

Unauthenticated runtime smoke returned expected login redirects; no authenticated session was available to Codex and auth was not bypassed:

```text
/coach 303 -> /login
/dashboard 303 -> /login
/stats 303 -> /login
/matches 303 -> /login
/settings/imports 303 -> /login
```

Journal after restart showed clean shutdown/startup and GET redirects, with no traceback/500 evidence.

## Production Safety

- production DB touched: yes, explicitly authorized backup/import/parser attempt;
- production files touched: yes, backup DB, retained raw demo and docs/report;
- production demo files deleted or moved: no;
- live import/parser run: yes, exactly one guarded Steam import attempt, one demo downloaded and parsed;
- persistent report generated: no;
- schema changed: no;
- full resync performed: no;
- bulk import performed: no;
- batch cap raised: no.

## Whether v0.8 Can Be Promoted

No.

Exact blocker: the first real post-refresh playable exact-date match was imported successfully, but recommendation `#5` did not receive an evaluation and progress did not update. The loop `recommendation #5 -> new match -> evaluation with metric_confidence -> progress update` is still not accepted.

## Remaining Risks

- A focused follow-up repair is required for the missing post-import recommendation evaluation trigger.
- Do not run another live Steam/import/parser attempt just to force evaluation; match `#72` now exists and should be enough for a controlled repair/acceptance path.
- Legacy active `grenades #3` and `map #4` remain `needs_refresh` and are not accepted for hard progress.
- `data/uploads` and `data/tmp` still live on the root filesystem; this run remained within the configured storage guard.
