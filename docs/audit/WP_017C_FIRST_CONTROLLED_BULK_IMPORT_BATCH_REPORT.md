# WP-017C First Controlled Bulk Import Batch Report

Date: 2026-07-05

## RESULT: PASS_WITH_WARNINGS

WP-017C executed the first controlled `v0.9` real-data import batch with the cap kept at `STEAM_IMPORT_MAX_DEMOS_PER_RUN=1`.

One terminal parent `steam_import_all` attempt was performed. It completed as `PASS_NO_NEW_MATCH`: Steam sync returned no new share codes, no demo was downloaded, no parser job ran, no new playable match was created, and no recommendation evaluation was created.

Runs 2 and 3 were not started. After Run 1, the cursor had no new Steam share code, so immediate additional attempts would be redundant and would risk turning the WP into an operator retry loop rather than a new controlled one-demo batch.

## Backup

Required pre-run backup:

```text
data/manual_backups/cs2_coach_before_wp017c_first_batch_20260705_015315.db
```

Backup SHA:

```text
36ccd84dc5c695af1c75a74f8d1059ade68a2a0355bb43aca1a7b473dd68f320  data/cs2_coach.db
36ccd84dc5c695af1c75a74f8d1059ade68a2a0355bb43aca1a7b473dd68f320  data/manual_backups/cs2_coach_before_wp017c_first_batch_20260705_015315.db
```

## DB SHA

| Point | SHA |
|---|---|
| before first run | `36ccd84dc5c695af1c75a74f8d1059ade68a2a0355bb43aca1a7b473dd68f320` |
| after Run 1 | `809fdd5a645baac27b89e8e36b9d22f186249cab14d133314382404eac283ddf` |
| final | `809fdd5a645baac27b89e8e36b9d22f186249cab14d133314382404eac283ddf` |

The DB changed because the authorized live no-new import created parent job `#27`, child job `#28`, and updated Steam sync/import job state. No schema change was made.

## Launch Method

Authenticated UI path was unavailable to this Codex session:

- `GET /settings/imports` returned `303` to `/login`;
- unauthenticated `POST /settings/imports/pull-all` returned `403`;
- no authenticated owner browser session was available.

The authorized shell fallback was used exactly once:

```bash
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

TMPDIR evidence:

- `systemctl show jc-coach -p Environment` included `TMPDIR=/opt/jc-coach/data/tmp`, `TEMP=/opt/jc-coach/data/tmp`, `TMP=/opt/jc-coach/data/tmp`;
- explicit shell probe with those variables resolved the storage guard temp dir to `/opt/jc-coach/data/tmp`;
- Run 1 parent `result_json.storage_preflight.settings.temp_dir` was `/opt/jc-coach/data/tmp`.

## Pre-Run State

| Item | Value |
|---|---:|
| git status | clean |
| root available before first live run, after backup | `18,319,175,680` bytes |
| `data/tmp` | empty / `0` bytes by `du -sb` |
| service | `jc-coach.service` active/running |
| queued/running parent jobs | none |
| total matches | `72` |
| playable demo matches | `20` |
| `steam_history` placeholders | `52` |
| demo parse artifacts | `20` |
| recommendation `#5` evaluations | `1` |
| recommendation `#5` completed_matches | `1` |
| legacy recommendation `#3` evaluations | `19` |
| legacy recommendation `#4` evaluations | `19` |

Latest successful imported real match before this WP remained match `#72`, `de_dust2`, with exact date source `steam_gc_match_time`. Match mode remained unknown; no Premier/Competitive/Wingman claim was made.

## Attempt Summary

| Run | Parent job | Child job | Classification | Result |
|---:|---|---|---|---|
| 1 | `#27 steam_import_all`, `succeeded` | `#28 match_history_sync`, `succeeded` | `PASS_NO_NEW_MATCH` | no new share code, no download, no parser, no new match |

Run 1 parent result:

```text
overall_outcome=no_new
statuses=["no_new", "exact_match_date_unavailable"]
clean_success=true
demo_download.processed=0
demo_download.imported=0
demo_download.failed=0
demo_download.pending=0
demo_download.results=[]
```

Run 1 child result:

```text
sync_outcome=SUCCESS_NO_NEW_MATCHES
collected=0
inserted=0
duplicates=0
cursor_advanced=false
last_share_code=CSGO-DearK-t4hWu-OUquu-aoKwy-KhMMB
```

## Per-Run Data Validation

Run 1:

| Check | Value |
|---|---|
| new share code | none |
| new playable demo match id | none |
| map_name | not applicable |
| match_date_status | not applicable |
| match_date_source | not applicable |
| parser artifact count for new match | not applicable; no new match |
| retained demo path/size | not applicable; no new demo |
| recommendation `#5` evaluation count before/after | `1 -> 1` |
| recommendation `#5` evaluation row for new match | none; no new match |
| `evidence_json.metric_confidence` present | not applicable; no new evaluation |
| recommendation `#5.completed_matches` before/after | `1 -> 1` |
| legacy `#3/#4` got new evaluations | no; counts stayed `19/19` |
| queued/running parent job after run | none |

## Storage Validation

| Point | root available bytes | uploads bytes | tmp bytes | manual_backups bytes | demo files |
|---|---:|---:|---:|---:|---:|
| before backup | `18,324,303,872` | `4,062,565,189` | `0` | `1,201,012,736` | `29` |
| before live run, after backup | `18,319,175,680` | `4,062,565,189` | `0` | about `1.2G` | `29` |
| after Run 1 | `18,243,694,592` | `4,062,565,189` | `0` | `1,276,076,032` | `29` |

Storage notes:

- `data/uploads` did not change.
- `.dem` / `.dem.bz2` count stayed `29`.
- `data/tmp` was empty after Run 1.
- `data/manual_backups` increased by the required DB backup.
- The DB file is `75,063,296` bytes; the backup file is also `75,063,296` bytes.
- Root free remained above the post-run `10 GiB` hard stop threshold.
- The storage guard reported only `upload_dir_on_small_root_warning`, which is an existing known layout warning, not a run failure.

## Service And Log Safety

Post-run service state:

```text
jc-coach.service active/running
Main PID: 146750
Memory: about 66.7M
```

Journal check since the run showed no traceback, no HTTP 500, and no exception entries. The service was not restarted.

## Match Mode Handling

No new match was imported in WP-017C. Existing playable match mode remains unknown from persisted data. This report does not infer Premier, Competitive or Wingman from map name.

## Production Safety

| Item | Status |
|---|---|
| production DB touched | yes; authorized backup plus import job/sync state writes |
| production files touched | yes; DB backup and documentation |
| production raw demo files touched | no delete, move, compression or new raw demo |
| live Steam import/sync run | yes; one parent `steam_import_all` job |
| live demo download run | no |
| parser job run | no |
| recommendation evaluation created | no |
| schema changed | no |
| app persistent report generated | no |
| AI coach rewrite | no |
| recommendation planner rewrite | no |
| commit made | no |

## WP-017D Readiness

WP-017D Post-Batch Data/Performance Acceptance can start as a no-new post-batch review.

It cannot accept new-demo parser/recommendation stability from WP-017C, because no new share code was available and no demo was downloaded or parsed. A future controlled run is still needed when Steam has a genuinely new match after the saved cursor.

## Remaining Risks

- Parser and post-import recommendation evaluation stability were not re-exercised by this no-new batch.
- Authenticated UI/page timing checks were not available to Codex; only unauthenticated redirects/403 were observed.
- `data/uploads` and `data/tmp` still live on the root filesystem.
- `ImportJob.status` remains coarse; `result_json` remains canonical.
- Match mode remains unknown unless future metadata capture proves otherwise.
