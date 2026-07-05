# WP-017C2 Controlled Import After New Match Report

Date: 2026-07-05

## RESULT: PASS_ONE_DEMO_IMPORTED_AND_EVALUATED

WP-017C2 ran exactly one controlled live Steam import attempt after the operator played a new Valve match.

Steam exposed two new share codes. The run obeyed the configured one-demo cap (`max_demos_per_run=1`): it downloaded, retained and parsed exactly one demo, then stopped with `overall_outcome=batch_cap_reached` and one pending share code left for a future authorized WP. Because `ImportJob.status` is coarse, the parent job is persisted as `failed`, but the one-demo objective for this controlled attempt passed.

Recommendation `#5` received exactly one new evaluation for the newly imported playable exact-date match. Legacy recommendations `#3` and `#4` received no new evaluations.

## Backup

Required pre-run backup:

```text
data/manual_backups/cs2_coach_before_wp017c2_after_new_match_20260705_030831.db
```

Backup SHA:

```text
809fdd5a645baac27b89e8e36b9d22f186249cab14d133314382404eac283ddf  data/cs2_coach.db
809fdd5a645baac27b89e8e36b9d22f186249cab14d133314382404eac283ddf  data/manual_backups/cs2_coach_before_wp017c2_after_new_match_20260705_030831.db
```

## DB SHA

| Point | SHA |
|---|---|
| before backup / before live attempt | `809fdd5a645baac27b89e8e36b9d22f186249cab14d133314382404eac283ddf` |
| after import before manual evaluation | `13ca96312fefdfabe3557190de0baff387cb2af59af5065af22c1fe34d46c8f6` |
| final after recommendation evaluation | `3a96e5dc3d7f4cb850183731dc74c44a1a413f233d5d9fc0f76b7acbe02f927d` |

Schema fingerprint stayed unchanged:

```text
8b14fbf33fdeb555f8bfa559424a46d6742de516a58f49ecc848b12b03921fc5
```

## Launch Method

Authenticated UI path was unavailable to Codex in the previous WP (`GET /settings/imports` redirected to login and unauthenticated POST returned `403`), so the authorized shell fallback was used exactly once:

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

- `systemctl show jc-coach -p Environment` showed `TMPDIR=/opt/jc-coach/data/tmp`, `TEMP=/opt/jc-coach/data/tmp`, `TMP=/opt/jc-coach/data/tmp`.
- The shell fallback explicitly pinned the same three variables.
- Parent job `#29` stored `storage_settings.temp_dir=/opt/jc-coach/data/tmp`.
- `data/tmp` was `0` bytes after the run.

## Pre-Run Verification

| Check | Value |
|---|---:|
| git status | clean |
| root available | `18,244,902,912` bytes |
| `data/tmp` | `0` bytes |
| service | `jc-coach.service` active/running |
| queued/running `steam_import_all` jobs | none |
| latest WP-017C jobs | parent `#27` succeeded, child `#28` succeeded |
| total matches | `72` |
| playable non-`steam_history` matches | `20` |
| demo source matches | `20` |
| `steam_history` placeholders | `52` |
| demo parse artifacts | `20` |
| recommendation `#5` evaluations | `1` |
| recommendation `#5.completed_matches` | `1/10` |
| legacy `#3/#4` evaluations | `19/19` |
| DB SHA | `809fdd5a645baac27b89e8e36b9d22f186249cab14d133314382404eac283ddf` |

## Import Job Outcomes

| Item | Value |
|---|---|
| parent job | `#29 steam_import_all` |
| parent status | `failed` |
| parent `overall_outcome` | `batch_cap_reached` |
| parent statuses | `batch_cap_reached`, `success`, `exact_match_date_available` |
| child job | `#30 match_history_sync` |
| child status | `succeeded` |
| child outcome | `SUCCESS_NEW_MATCH_IMPORTED` |
| collected share codes | `2` |
| inserted share-code placeholders | `2` |
| demo download processed/imported/failed | `1/1/0` |
| remaining pending | `1` |

New share codes:

```text
CSGO-owEoV-4o9Uj-kK5Fp-4zYKz-UqDZG
CSGO-wuo7M-UmvYG-NQuTA-FjkR4-SpeOQ
```

The first collected share code remains a pending `steam_history` placeholder (`match #73`). The second was downloaded and parsed through the one-demo cap.

## New Match Validation

| Field | Value |
|---|---|
| pending placeholder | `match #73`, `source=steam_history`, no exact date yet |
| imported placeholder | `match #74`, `source=steam_history`, raw status `demo_imported` |
| playable match | `match #75` |
| playable source | `demo` |
| share code | `CSGO-wuo7M-UmvYG-NQuTA-FjkR4-SpeOQ` |
| played_at | `2026-07-04 20:26:32` |
| map_name | `de_overpass` |
| result | `loss`, `5-13` |
| match_date_status | `exact_match_date_available` |
| match_date_source | `steam_gc_match_time` |
| date truth | exact |

## Parser Validation

| Field | Value |
|---|---|
| parser artifact | `demo_parse_artifacts.id=50` |
| match_id | `75` |
| parser | `demoparser2 0.41.3` |
| status | `parsed` |
| raw demo path | `/opt/jc-coach/data/uploads/20260705000903_da30ec03de_CSGO-wuo7M-UmvYG-NQuTA-FjkR4-SpeOQ.dem` |
| raw demo exists | yes |
| raw demo size | `234,943,374` bytes |
| metric confidence in artifact | yes |

Parser/import payload preserved `match_date_status=exact_match_date_available` and `match_date_source=steam_gc_match_time`.

## Recommendation #5 Validation

Automatic post-import evaluation did not create a row during the import itself. The WP explicitly allowed creating recommendation evaluation for `#5` when the new match was playable exact-date, so the existing evaluator was run once for match `#75`.

Created evaluation:

| Field | Value |
|---|---|
| evaluation id | `77` |
| recommendation id | `5` |
| match id | `75` |
| status | `red` |
| score | `0` |
| `evidence_json.metric_confidence` | present |

Progress:

| Metric | Before | After |
|---|---:|---:|
| recommendation `#5` evaluations | `1` | `2` |
| recommendation `#5.completed_matches` | `1/10` | `2/10` |
| recommendation `#5` counts | `green=1, red=0` | `green=1, red=1` |
| recommendation `#5` progress score | not re-recorded | `10/100` |

## Legacy Safety

Legacy recommendation counts stayed unchanged:

| Recommendation | Before | After |
|---|---:|---:|
| `#3 grenades` | `19` | `19` |
| `#4 map` | `19` | `19` |

Both remain `needs_refresh` and are not accepted for hard progress.

## Storage Delta

| Point | root available bytes | uploads bytes | tmp bytes | manual_backups bytes | demo files |
|---|---:|---:|---:|---:|---:|
| before run | `18,244,902,912` | `4,062,565,189` | `0` | `1,276,076,032` | `29` |
| after run/evaluation | `17,929,482,240` | `4,297,508,563` | `0` | `1,351,139,328` | `30` |
| delta | `-315,420,672` | `+234,943,374` | `0` | `+75,063,296` | `+1` |

The upload delta is explained by the one retained raw demo. The manual backup delta is explained by the required DB backup. `data/tmp` was cleaned.

Root free remained above 12 GiB after the run.

## Service And Log Safety

Post-run service state:

```text
jc-coach.service active/running
Main PID: 146750
```

`journalctl -u jc-coach --since '2026-07-05 00:08:00' --until '2026-07-05 00:12:00'` returned no entries. The shell attempt itself produced no traceback. No HTTP 500 was observed in the captured service status output.

## Match Mode Handling

Playable match `#75` persisted `mode=demo`, which is parser/import provenance, not Valve playlist classification. No Premier/Competitive/Wingman claim is made. The `steam_history` placeholders show `Valve Matchmaking`, but this is not treated as sufficient proof of exact mode.

## Production Safety

| Item | Status |
|---|---|
| production DB touched | yes; authorized backup, import jobs/matches/artifact/evaluation writes |
| production files touched | yes; DB backup, one retained raw demo, documentation |
| raw demo deleted/moved/compressed | no |
| live import/parser run | yes; exactly one parent import attempt, one demo downloaded/parsed |
| schema changed | no |
| persistent app report generated | no |
| AI coach rewrite | no |
| recommendation planner rewrite | no |
| commit made | no |

## WP-017D Readiness

WP-017D can start, but it should treat WP-017C2 as a one-demo pass with a batch-cap warning, not as a full bulk import acceptance.

WP-017D should specifically review:

- parent job `#29` persisted as `failed` because `batch_cap_reached` is not a clean-success outcome, despite one successful demo import;
- pending placeholder `#73` from the second new share code;
- storage growth from one retained raw demo;
- whether auto post-import recommendation evaluation should have fired without manual evaluator invocation.

Do not raise the demo cap until WP-017D accepts this evidence.

## Remaining Risks

- `ImportJob.status` remains coarse; `result_json` is still canonical for partial success / batch-cap truth.
- One pending new share code remains intentionally unprocessed due to the cap.
- Automatic post-import recommendation evaluation did not create evaluation `#77`; it required the explicitly allowed manual evaluator call.
- Raw demos remain retained on the root filesystem.
- Match mode remains unknown unless reliable metadata is captured or recovered.
- Authenticated UI timing was not captured by Codex.
