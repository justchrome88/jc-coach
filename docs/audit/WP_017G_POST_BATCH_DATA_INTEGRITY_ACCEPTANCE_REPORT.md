# WP-017G Post-Batch Data Integrity Acceptance Report

Date: 2026-07-05

## RESULT: ACCEPTED_WITH_WARNINGS

WP-017 real-data onboarding data integrity is accepted for the controlled one-demo/no-new/repaired-pending path. The database, retained demo files, parser artifacts, exact-date truth and recommendation evaluations are internally consistent after WP-017F.

This does not promote `v0.9` and does not authorize raising the Steam demo cap. Performance acceptance and metadata/process warnings remain.

## Product Version Observed

`v0.8`

Target remains `v0.9` Real Data Onboarding / Bulk Demo Usage.

## DB SHA

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

Schema fingerprint:

```text
03686922b7a4614379ef689b78ed7f5327cc6331862cffe946eb22f5ea28c368
```

Schema changed: no.

## Data Inventory

| Item | Value |
|---|---:|
| total matches | `76` |
| source=`demo` | `22` |
| source=`steam_history` | `54` |
| playable matches | `22` |
| playable demo matches | `22` |
| exact playable dates | `20` |
| approximate playable dates | `2` |
| unknown playable dates | `0` |
| coach reports | `0` |

Playable demo map distribution:

| Map | Count |
|---|---:|
| `de_ancient` | `4` |
| `de_cache` | `1` |
| `de_dust2` | `7` |
| `de_inferno` | `1` |
| `de_mirage` | `2` |
| `de_nuke` | `2` |
| `de_overpass` | `5` |

Latest rows:

| Row | Source | Status | Linked Demo | Map | Exact Date |
|---:|---|---|---:|---|---|
| `#73` | `steam_history` | `demo_imported` | `#76` | n/a | metadata only |
| `#74` | `steam_history` | `demo_imported` | `#75` | n/a | metadata only |
| `#75` | `demo` | `parsed` | self | `de_overpass` | yes |
| `#76` | `demo` | `parsed` | self | `de_mirage` | yes |

## Steam Placeholder Integrity

| Placeholder | Share Code | Status | imported_demo_match_id | Notes |
|---:|---|---|---:|---|
| `#73` | `CSGO-owEoV-4o9Uj-kK5Fp-4zYKz-UqDZG` | `demo_imported` | `76` | contains `recommendation_evaluations` metadata for `#78` |
| `#74` | `CSGO-wuo7M-UmvYG-NQuTA-FjkR4-SpeOQ` | `demo_imported` | `75` | historical WP-017C2 placeholder |

Steam history status counts:

| Status | Count |
|---|---:|
| `demo_download_pending` | `37` |
| `demo_imported` | `16` |
| `demo_download_error` | `1` |

The 37 pending rows are older/stale history rows from prior cursor walks, not WP-017C2/F leftovers. The specific WP-017C2/F pending row `#73` is no longer pending.

Queued/running `steam_import_all`: none.

Historical queue warning: two old non-parent Steam jobs are still `queued`:

| Job | Type | Status | Created |
|---:|---|---|---|
| `#1` | `steam_openid_linked` | `queued` | `2026-07-01 12:51:51` |
| `#10` | `match_history_sync` | `queued` | `2026-07-02 22:42:41` |

They predate WP-017 and were not processed in WP-017G. They should be handled by a later explicit cleanup/repair WP if needed.

## Demo File Integrity

| Check | Value |
|---|---:|
| demo files in `data/uploads` | `31` |
| non-null `matches.demo_file` references | `16` unique paths |
| missing `matches.demo_file` targets | `0` |
| artifact `source_demo_file` references | `22` unique paths |
| unreferenced by `matches.demo_file` | `15` files |
| unreferenced by match or artifact | `15` files |

The 15 unreferenced files are pre-existing retained/raw development artifacts and failed/old import files. WP-017G did not delete or move them.

Specific retained demos:

| Match | Path | Size | Exists |
|---:|---|---:|---|
| `#75` | `/opt/jc-coach/data/uploads/20260705000903_da30ec03de_CSGO-wuo7M-UmvYG-NQuTA-FjkR4-SpeOQ.dem` | `234,943,374` | yes |
| `#76` | `/opt/jc-coach/data/uploads/20260705004200_c7ddbe940b_CSGO-owEoV-4o9Uj-kK5Fp-4zYKz-UqDZG.dem` | `163,680,743` | yes |

## Parser Artifact Integrity

| Check | Value |
|---|---:|
| `demo_parse_artifacts` rows | `22` |
| playable demo matches without artifact | `0` |
| parser status counts | `parsed=22` |

Special rows:

| Match | Artifact | Parser | Status | `confidence_json.metric_confidence` | `match.raw_json.metric_confidence` |
|---:|---:|---|---|---|---|
| `#75` | `#50` | `demoparser2 0.41.3` | `parsed` | present | present |
| `#76` | `#51` | `demoparser2 0.41.3` | `parsed` | present | present |

`payload_json` itself does not include `metric_confidence`; confidence is stored in `confidence_json` and match `raw_json`.

## Recommendation Integrity

Recommendation `#5` is active and accepted:

| Field | Value |
|---|---|
| category | `survival` |
| status | `active` |
| health.needs_refresh | `false` |
| accepted_for_hard_progress | `true` |
| evaluations | `#76`, `#77`, `#78` |
| completed_matches | `3/10` |
| progress_score | `15` |

Recommendation `#5` evaluations:

| Evaluation | Match | Status | Score | Metric Confidence |
|---:|---:|---|---:|---|
| `#76` | `#72` | `green` | `90` | present |
| `#77` | `#75` | `red` | `0` | present |
| `#78` | `#76` | `yellow` | `45` | present |

Duplicate evaluation check: no duplicate `(recommendation_id, match_id)` rows.

Legacy safety:

| Recommendation | Status | Health | Eval Count | Eval Rows On `#75/#76` |
|---:|---|---|---:|---:|
| `#1 survival` | `archived` | `needs_refresh=true` | `19` | `0` |
| `#3 grenades` | `active` | `needs_refresh=true` | `19` | `0` |
| `#4 map` | `active` | `needs_refresh=true` | `19` | `0` |

## Import Job Integrity

WP-017C no-new path:

| Job | Type | Status | Canonical Result |
|---:|---|---|---|
| `#27` | `steam_import_all` | `succeeded` | `overall_outcome=no_new`, `demo_download.processed=0` |
| `#28` | `match_history_sync` | `succeeded` | `SUCCESS_NO_NEW_MATCHES`, `collected=0` |

WP-017C2 one-demo batch-cap path:

| Job | Type | Status | Canonical Result |
|---:|---|---|---|
| `#29` | `steam_import_all` | `failed` | `overall_outcome=batch_cap_reached`; demo import succeeded but one pending share code remained |
| `#30` | `match_history_sync` | `succeeded` | collected `#73/#74` share codes |

The `#29.status=failed` value is a coarse status limitation. Canonical interpretation is in `result_json`: `demo_download.processed=1`, `imported=1`, `failed=0`, `pending=1`, `batch_cap_reached=true`.

WP-017F targeted pending path:

- no new parent `steam_import_all` job;
- no new child `match_history_sync` job;
- metadata is present in returned service result and `matches.id=73.raw_json`.

## Storage Integrity

| Item | Value |
|---|---:|
| root available | `17,687,240,704` bytes |
| `/tmp` available | `1,400,332,288` bytes |
| `data/uploads` | `4,461,189,306` bytes |
| `data/tmp` | `0` bytes |
| `data/manual_backups` | `1,426,202,624` bytes |
| demo files | `31` |

Storage growth from WP-017C2/F is explained by retained raw demos `#75/#76` and manual DB backups. Root free remains above the safety threshold, but uploads/backups are still on root-backed storage.

Systemd temp environment:

```text
TMPDIR=/opt/jc-coach/data/tmp
TEMP=/opt/jc-coach/data/tmp
TMP=/opt/jc-coach/data/tmp
```

With explicit temp env, storage guard settings resolve to:

```text
max_demos_per_run=1
upload_dir=/opt/jc-coach/data/uploads
temp_dir=/opt/jc-coach/data/tmp
```

## Match Mode Handling

No Premier/Competitive/Wingman claim is accepted.

- `#75.mode=demo`
- `#76.mode=demo`
- `#73/#74.mode=Valve Matchmaking`

These are provenance/class labels only. They do not prove Valve playlist mode.

## Accepted Evidence

- No-new controlled path `#27/#28` is consistent.
- Batch-cap one-demo path `#29/#30` is consistent when interpreted through `result_json`.
- Pending `#73` was cleared by WP-017F and points to playable match `#76`.
- Matches `#75/#76` are exact-date playable demo rows with parser artifacts and retained raw demos.
- Recommendation `#5` has exactly three evaluations and progressed to `3/10`.
- Evaluation `#78` proves the repaired automatic evaluation path on live data.
- Legacy recommendations `#1/#3/#4` received no evaluations for `#75/#76`.
- No duplicate recommendation evaluations exist.
- `data/tmp` is clean and service logs show no traceback/500 during the checked window.

## Warnings Carried Forward

- Targeted pending-demo path lacks a parent `steam_import_all` result JSON, so job history alone does not show WP-017F evaluation metadata.
- Two historical queued non-parent Steam jobs remain: `#1 steam_openid_linked` and `#10 match_history_sync`.
- Authenticated UI performance acceptance is still not completed by this WP.
- Match mode remains provenance-only/unknown for Premier/Competitive/Wingman.
- Raw demos and manual backups are on root-backed storage.
- 15 retained demo files are unreferenced by current `matches.demo_file` or parser artifact paths; they are historical artifacts and were not modified.
- Cap remains `1`; no evidence yet supports raising it.

## Whether WP-017H Performance Acceptance Can Start

Yes. WP-017H should be a read-only runtime/UI performance and service acceptance pass for the current data volume.

## Whether Cap Can Be Raised Now

No. Cap remains `1`. A cap raise should wait until performance acceptance and a separate explicit cap-change WP.

## Whether v0.9 Can Be Promoted Now

No. Data integrity is accepted with warnings, but performance acceptance remains outstanding and the metadata/storage warnings must be carried forward.

## Next Recommended WP

`WP-017H Performance Acceptance`.

Recommended scope:

- authenticated UI/page timing if owner session is available;
- service memory/log review under current 22-demo data volume;
- no live import/parser/evaluator jobs;
- no cap raise;
- no schema changes.

## Safety Declarations

| Item | Status |
|---|---|
| production DB touched | no |
| production files touched | no runtime files; repository report/docs only |
| live import/parser run | no |
| manual evaluator run | no |
| schema changed | no |
| persistent app reports generated | no |
| commit made | no |
