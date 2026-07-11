# WP-017D Post-Batch Acceptance And Evaluation Trigger Diagnosis

Date: 2026-07-05

## RESULT: ACCEPT_WITH_REPAIR_REQUIRED

WP-017C/WP-017C2 batch evidence is acceptable as a controlled one-demo real-data onboarding pass, but not sufficient to promote `v0.9`.

Import, parser, storage and manual recommendation evaluation data are healthy. The blocker is reliability of the automatic post-import recommendation evaluation trigger in the Steam import path. The new playable exact-date match `#75` was eligible after Steam date truth was applied, but the automatic trigger ran earlier, before the row satisfied exact-date eligibility.

## Product Version Observed

`v0.8`

Target remains `v0.9` Real Data Onboarding / Bulk Demo Usage.

## DB SHA

```text
3a96e5dc3d7f4cb850183731dc74c44a1a413f233d5d9fc0f76b7acbe02f927d  data/cs2_coach.db
```

Schema fingerprint from read-only DB inspection:

```text
8b14fbf33fdeb555f8bfa559424a46d6742de516a58f49ecc848b12b03921fc5
```

## Data Inventory After WP-017C2

| Item | Value |
|---|---:|
| total matches | `75` |
| playable non-`steam_history` matches | `21` |
| playable demo matches | `21` |
| `steam_history` placeholders | `54` |
| exact playable dates | `19` |
| approximate playable dates | `2` |
| unknown playable dates | `0` |
| demo parse artifacts | `21` |
| playable matches with artifact | `21` |
| coach reports | `0` |
| max match id | `75` |
| max evaluation id | `77` |

No queued/running `steam_import_all` jobs were present.

## WP-017C/C2 Batch Evidence

WP-017C:

- parent job `#27`: `succeeded`, `overall_outcome=no_new`;
- child job `#28`: `succeeded`, `SUCCESS_NO_NEW_MATCHES`;
- no demo download, parser run, playable match or evaluation.

WP-017C2:

- parent job `#29`: persisted `failed`, `overall_outcome=batch_cap_reached`;
- child job `#30`: `succeeded`, `SUCCESS_NEW_MATCH_IMPORTED`;
- two share codes collected, two placeholders inserted;
- cap `1` was respected: `processed=1`, `imported=1`, `failed=0`, `remaining_pending=1`;
- one playable demo match created: `#75`.

Parent `#29` failed status is a coarse-status artifact. Canonical result is `result_json`: one successful demo import plus batch-cap stop.

## Pending Share Code #73 Status

`match #73`:

| Field | Value |
|---|---|
| source | `steam_history` |
| share code | `CSGO-owEoV-4o9Uj-kK5Fp-4zYKz-UqDZG` |
| raw status | `demo_download_pending` |
| next step | `download_demo_with_steam_service_bot` |
| demo_file | `NULL` |
| exact date | unavailable |

It is pending and unprocessed. It must not be processed until the auto-evaluation trigger is repaired or an explicit future WP accepts manual-only evaluation as policy.

## Match #75 Validation

| Field | Value |
|---|---|
| id | `75` |
| source | `demo` |
| map | `de_overpass` |
| mode | `demo` provenance only |
| played_at | `2026-07-04 20:26:32` |
| date status | `exact_match_date_available` |
| date source | `steam_gc_match_time` |
| raw demo | `/opt/jc-coach/data/uploads/20260705000903_da30ec03de_CSGO-wuo7M-UmvYG-NQuTA-FjkR4-SpeOQ.dem` |
| raw demo size | `234,943,374` bytes |
| raw demo SHA256 | `0bd7d73ab568291a5f304b4d46de91e1828a80467b95bef150d6b4d81bd9ff38` |

No Premier/Competitive/Wingman claim is made. `mode=demo` is parser/import provenance, not Valve playlist classification.

## Evaluation #77 Validation

| Field | Value |
|---|---|
| id | `77` |
| recommendation_id | `5` |
| match_id | `75` |
| status | `red` |
| score | `0` |
| evaluated_at | `2026-07-05 00:10:09` |
| `evidence_json.metric_confidence` | present |

Evaluation `#77` was created after the import job ended. Parent job `#29.finished_at` was `2026-07-05 00:09:20.525976`; evaluation `#77.evaluated_at` was `2026-07-05 00:10:09`.

This timing confirms `#77` was the explicit manual evaluator call from WP-017C2, not an automatic import-side evaluation.

## Recommendation #5 Progress

Recommendation `#5`:

| Field | Value |
|---|---:|
| category | `survival` |
| status | `active` |
| start_after_match_id | `70` |
| target period | `10` |
| evaluation count | `2` |
| completed_matches | `2/10` |
| progress_score | `10/100` |
| evaluations | `#76`, `#77` |

The progress increment is valid, but it depended on the explicit manual evaluator call.

## Legacy Recommendation Safety

Legacy active recommendations stayed unchanged:

| Recommendation | Evaluation Count | Last Evaluation |
|---|---:|---|
| `#3 grenades` | `19` | `#73` on match `#70` |
| `#4 map` | `19` | `#74` on match `#70` |

They remain legacy/needs-refresh and are not accepted for hard progress.

## Storage Validation

| Item | Value |
|---|---:|
| root available | `17,928,413,184` bytes |
| `/tmp` available | `1,403,219,968` bytes |
| `data/uploads` | `4,297,508,563` bytes |
| `data/tmp` | `0` bytes |
| `data/manual_backups` | `1,351,139,328` bytes |
| demo files | `30` |

The retained raw demo for match `#75` exists and matches the reported size. `data/tmp` is clean. Root free remains above the WP guard threshold.

## Service/Log Safety

`jc-coach.service` is active/running with environment pinned:

```text
TMPDIR=/opt/jc-coach/data/tmp
TEMP=/opt/jc-coach/data/tmp
TMP=/opt/jc-coach/data/tmp
```

Journal scan since the WP-017C2 import window found no traceback, exception, error or HTTP 500 lines. Recent logs show normal authenticated owner GETs for `/coach`, `/matches` and `/matches/75`.

Authenticated performance acceptance remains limited: no browser session was provided to Codex for systematic timing checks. Unauthenticated redirects are service-alive evidence only, not UI performance acceptance.

## Auto-Evaluation Trigger Diagnosis

Intended WP-016E4 contract:

- `import_demo_file(...)` creates the new playable `Match`;
- `_save_demo_parse_artifacts(...)` stores parser evidence;
- `evaluate_recommendations_for_match(db, match.id)` evaluates the specific new match;
- result payload should include compact `recommendation_evaluations`.

Current code path:

- `demo_parser.import_demo_file(...)` calls `evaluate_recommendations_for_match(db, match.id)` at [demo_parser.py:144](/opt/jc-coach/app/services/demo_parser.py:144).
- `evaluate_recommendations_for_match(...)` first searches for the match in `_ordered_matches(db)` at [recommendation_tracking.py:125](/opt/jc-coach/app/services/recommendation_tracking.py:125).
- `_ordered_matches(...)` returns only exact-date playable matches through `exact_recent_matches(...)` at [recommendation_tracking.py:907](/opt/jc-coach/app/services/recommendation_tracking.py:907).
- exact-date eligibility requires `match_date_status=exact_match_date_available` and `match_date_source=steam_gc_match_time` at [metric_confidence.py:240](/opt/jc-coach/app/services/metric_confidence.py:240).
- In the Steam path, `_download_and_import_match(...)` calls `import_demo_file(...)` first at [steam_demo_downloader.py:308](/opt/jc-coach/app/services/steam_demo_downloader.py:308), then applies primary Steam date truth only after that returns at [steam_demo_downloader.py:348](/opt/jc-coach/app/services/steam_demo_downloader.py:348).

Therefore, during automatic evaluation, the new row is not yet eligible for `_ordered_matches(...)`. After `_apply_primary_steam_date_truth(...)` runs, the same match becomes exact-date eligible; the manual evaluator then creates `#77`.

Additional metadata issue:

- `import_demo_file(...)` returns `recommendation_evaluations`, but `_download_and_import_match(...)` does not include that field in the parent `demo_download.results` return payload at [steam_demo_downloader.py:376](/opt/jc-coach/app/services/steam_demo_downloader.py:376).
- DB result metadata for job `#29` has no `recommendation_evaluations` key in `demo_download.results[0]`.
- Artifact `#50.payload_json` and match `#75.raw_json` also have no `recommendation_evaluations` key.

This omission makes missed automatic evaluations harder to detect from job metadata.

## Root Cause

Known root cause: ordering mismatch in the Steam downloader path.

`import_demo_file(...)` evaluates too early for Steam imports. The new playable match exists, but authoritative Steam exact-date truth is applied after the targeted evaluation call. Because recommendation evaluation intentionally filters to exact-date playable matches, the helper returns an empty list without error.

Batch-cap status did not directly skip evaluation. The batch cap is classified after downloader results return. It explains parent job `#29.status=failed`, but the missed automatic evaluation occurred earlier inside the successful one-demo import path.

No evidence indicates a swallowed exception. The shell fallback path called the same service functions as the web background path; the difference from the WP-016E4 manual production evaluation is timing, not shell-vs-UI behavior.

## Repair Requirement

Code repair is required before the next import.

The repair should make Steam import apply exact Steam date truth before calling `evaluate_recommendations_for_match(...)`, or re-run targeted evaluation after `_apply_primary_steam_date_truth(...)` commits the imported playable match. It should also carry compact `recommendation_evaluations` into `demo_download.results` and parent job `result_json` so missed evaluations are visible.

## Pending #73 Decision

Pending `#73` must wait.

Do not process it until the auto-evaluation trigger is repaired and verified, or until a future WP explicitly accepts a manual-only evaluation policy. Manual-only is not preferred for `v0.9`.

## Cap Decision

Do not raise the cap to `2`.

The one-demo cap protected storage and kept blast radius small. Since the automatic evaluation trigger is not reliable, increasing throughput would multiply the failure mode and create more manual reconciliation work.

## v0.9 Acceptance Status

`v0.9` is not accepted and must not be promoted yet.

Accepted from WP-017C/C2:

- controlled shell fallback with explicit temp env works;
- cap `1` is respected;
- one demo can be downloaded, retained and parsed;
- exact Steam GC date truth can be persisted;
- storage remains bounded and `data/tmp` is cleaned;
- manual targeted evaluation can evaluate the imported match with `metric_confidence`;
- legacy recommendations remain untouched.

Not accepted:

- automatic post-import recommendation evaluation reliability;
- cap increase;
- pending share-code continuation;
- full authenticated UI/page performance acceptance.

## Next Recommended WP

Next recommended WP: `WP-017E Auto-Evaluation Trigger Repair for Steam Batch Import Path`.

Scope should be narrow:

- fix evaluation timing for Steam imports;
- preserve exact-date gating;
- surface `recommendation_evaluations` in parent job metadata;
- add targeted tests for Steam import result/evaluation timing;
- then process pending `#73` in a later controlled one-demo WP.

The existing match-mode classification WP should wait until this reliability issue is closed or be renumbered behind the repair.

## Production Safety

| Item | Status |
|---|---|
| production DB touched | no; read-only DB inspection only |
| production files touched | yes; this audit report only |
| live import/parser run | no |
| manual evaluator run | no |
| pending `#73` processed | no |
| raw demo deleted/moved/compressed | no |
| persistent app report generated | no |
| runtime code changed | no |
| tests changed | no |
| schema changed | no |
| commit made | no |
