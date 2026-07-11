# WP-017F Controlled Pending Share Code #73 Import Report

Date: 2026-07-05

## RESULT: PASS_PENDING_73_IMPORTED_AND_AUTO_EVALUATED

Pending Steam history match `#73` was processed in exactly one controlled live pending-demo attempt. The run downloaded, retained and parsed one demo, created playable exact-date demo match `#76`, and the repaired automatic post-import evaluation path created recommendation evaluation `#78` for recommendation `#5` without a manual evaluator call.

Important metadata limitation: WP-017F used the smallest safe official pending-demo path, `download_pending_steam_demos(..., share_codes=[#73], limit=1)`, rather than `import_all_available_steam_matches(...)`. This avoided a broader match-history sync/resync and targeted only `#73`, but it did not create a new `steam_import_all` parent job or child `match_history_sync` job. Recommendation metadata is present in the returned service result and in placeholder `#73.raw_json`, not in a new parent `ImportJob.result_json`.

## Backup Path

```text
data/manual_backups/cs2_coach_before_wp017f_pending_73_import_20260705_034135.db
```

Backup SHA:

```text
3a96e5dc3d7f4cb850183731dc74c44a1a413f233d5d9fc0f76b7acbe02f927d  data/cs2_coach.db
3a96e5dc3d7f4cb850183731dc74c44a1a413f233d5d9fc0f76b7acbe02f927d  data/manual_backups/cs2_coach_before_wp017f_pending_73_import_20260705_034135.db
```

## DB SHA Before/After/Final

| Point | SHA |
|---|---|
| before backup / before live attempt | `3a96e5dc3d7f4cb850183731dc74c44a1a413f233d5d9fc0f76b7acbe02f927d` |
| after live attempt / final observed | `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33` |

Schema fingerprint stayed unchanged:

```text
03686922b7a4614379ef689b78ed7f5327cc6331862cffe946eb22f5ea28c368
```

## Launch Method

Shell fallback with explicit temp environment, using the official pending-demo downloader path:

```bash
TMPDIR=/opt/jc-coach/data/tmp \
TEMP=/opt/jc-coach/data/tmp \
TMP=/opt/jc-coach/data/tmp \
.venv/bin/python - <<'PY'
from app.db.session import SessionLocal
from app.services.steam_demo_downloader import download_pending_steam_demos

with SessionLocal() as db:
    result = download_pending_steam_demos(
        db,
        limit=1,
        share_codes=["CSGO-owEoV-4o9Uj-kK5Fp-4zYKz-UqDZG"],
    )
PY
```

## TMPDIR Evidence

`systemctl show jc-coach -p Environment`:

```text
Environment=PYTHONUNBUFFERED=1 TMPDIR=/opt/jc-coach/data/tmp TEMP=/opt/jc-coach/data/tmp TMP=/opt/jc-coach/data/tmp
```

The shell command pinned the same `TMPDIR`, `TEMP` and `TMP` values. `data/tmp` was `0` bytes after the run.

## Pending #73 Pre-State

| Field | Value |
|---|---|
| id | `73` |
| source | `steam_history` |
| share code | `CSGO-owEoV-4o9Uj-kK5Fp-4zYKz-UqDZG` |
| raw status | `demo_download_pending` |
| next step | `download_demo_with_steam_service_bot` |
| demo_file | `NULL` |

## Import Job IDs / Status / Outcomes

No new parent or child import job was created by this narrow pending-demo path.

Latest existing jobs remained:

| Job | Type | Status | Note |
|---|---|---|---|
| `#29` | `steam_import_all` | `failed` | historical WP-017C2 parent, `overall_outcome=batch_cap_reached` |
| `#30` | `match_history_sync` | `succeeded` | historical WP-017C2 child |

No queued/running `steam_import_all` jobs existed before or after the run.

Live attempt result:

| Field | Value |
|---|---:|
| configured | `true` |
| processed | `1` |
| imported | `1` |
| failed | `0` |
| skipped | `0` |
| pending | `0` |
| remaining_pending | `0` |
| batch_cap_reached | `false` |
| budget_status | `null` |

## Processed Share Code

```text
CSGO-owEoV-4o9Uj-kK5Fp-4zYKz-UqDZG
```

Placeholder `#73` now has `raw_json.status=demo_imported`, `demo_file` pointing at the retained raw demo, and `imported_demo_match_id=76`.

## New Playable Match Validation

| Field | Value |
|---|---|
| id | `76` |
| source | `demo` |
| share code | `CSGO-owEoV-4o9Uj-kK5Fp-4zYKz-UqDZG` |
| played_at | `2026-07-04 20:04:48` |
| map_name | `de_mirage` |
| result | `win`, `13-1` |
| mode | `demo` provenance only |
| match_date_status | `exact_match_date_available` |
| match_date_source | `steam_gc_match_time` |
| played_at_source | `steam_gc_match_time` |

Match mode handling: no Premier/Competitive/Wingman claim is made. Persisted `mode=demo` is parser/import provenance, not Valve playlist classification.

## Parser Validation

| Field | Value |
|---|---|
| parser artifact | `demo_parse_artifacts.id=51` |
| match_id | `76` |
| parser | `demoparser2 0.41.3` |
| status | `parsed` |
| raw demo path | `/opt/jc-coach/data/uploads/20260705004200_c7ddbe940b_CSGO-owEoV-4o9Uj-kK5Fp-4zYKz-UqDZG.dem` |
| raw demo exists | yes |
| raw demo size | `163,680,743` bytes |
| artifact `confidence_json.metric_confidence` | present |

## Automatic Evaluation Validation

Created automatically during import:

| Field | Value |
|---|---|
| evaluation id | `78` |
| recommendation id | `5` |
| match id | `76` |
| status | `yellow` |
| score | `45` |
| evaluated_at | `2026-07-05 00:42:11` |
| `evidence_json.metric_confidence` | present |

No manual evaluator was run and no evaluation row was inserted manually.

## Recommendation Evaluations Metadata Validation

The live attempt returned compact metadata:

```json
{
  "recommendation_evaluations": [
    {
      "id": 78,
      "recommendation_id": 5,
      "match_id": 76,
      "status": "yellow",
      "score": 45
    }
  ],
  "recommendation_evaluation": {
    "status": "created",
    "count": 1,
    "match_id": 76
  }
}
```

The same metadata is persisted in `matches.id=73.raw_json` under `recommendation_evaluations` and `recommendation_evaluation`.

No new parent `ImportJob.result_json` exists for this attempt because the safe path intentionally avoided `steam_import_all` and full match-history sync. This is a metadata-surface limitation to address before relying on parent job history for targeted pending-only imports.

## Recommendation #5 Progress Validation

| Metric | Before | After |
|---|---:|---:|
| recommendation `#5` evaluations | `2` | `3` |
| completed_matches | `2/10` | `3/10` |
| progress_score | `10` | `15` |
| evaluation for match `#76` | `0` | `1` |

## Legacy Safety

| Recommendation | Before | After |
|---|---:|---:|
| archived `#1` | `19` | `19` |
| legacy `#3 grenades` | `19` | `19` |
| legacy `#4 map` | `19` | `19` |

No legacy or archived recommendation received a new evaluation.

## Storage Delta

| Item | Before | After | Delta |
|---|---:|---:|---:|
| `data/uploads` bytes | `4,297,508,563` | `4,461,189,306` | `+163,680,743` |
| demo files | `30` | `31` | `+1` |
| `data/tmp` bytes | `0` | `0` | `0` |
| `data/manual_backups` bytes | `1,351,139,328` | `1,426,202,624` | `+75,063,296` |
| root available bytes | `17,930,199,040` | `17,687,826,432` | `-242,372,608` |

The upload delta is exactly the retained raw demo size. Root free remains above `10 GiB`.

## Service / Log Safety

`jc-coach.service` remained active/running after the attempt. Memory was about `220.8M`, peak `241.4M`.

Journal scan since `2026-07-05 03:41:00` found no traceback, exception, error or HTTP 500 lines.

## Safety Declarations

| Item | Status |
|---|---|
| production DB touched | yes, authorized backup/live import/parser/evaluation writes |
| production files touched | yes, DB backup and one retained raw demo |
| live import/parser run | yes, exactly one pending demo |
| manual evaluator run | no |
| pending `#73` processed | yes |
| schema changed | no |
| cap changed | no |
| raw demo files deleted/moved/compressed | no |
| persistent app reports generated | no, coach report count stayed `0` |

## Whether WP-017G Data Integrity Acceptance Can Start

Yes. WP-017G can start as a read-only data integrity / acceptance gate for the repaired-path live result.

Do not raise cap to `2` until WP-017G accepts this data and explicitly permits a later cap-change WP.

## Remaining Risks

- The targeted pending-demo path does not create parent `steam_import_all` job metadata. Evaluation metadata is visible in the returned service result and placeholder raw JSON, but not in a new parent job result JSON.
- Raw demos remain retained on root-backed storage; storage growth is still an operational risk.
- Match mode remains unknown beyond parser provenance.
- v0.9 is not promoted until WP-017G reviews data integrity, runtime safety and documentation state.
