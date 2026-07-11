# WP-016F Promote Recommendation Loop To v0.8 Report

Date: 2026-07-04

## RESULT: PROMOTED

WP-016 Recommendation Loop Acceptance is promoted to `v0.8` for controlled personal MVP runtime.

This was a documentation/status promotion only. Runtime code, tests, schema, production DB data, production demo files, live Steam/Valve import, demo downloads, parser jobs and persistent reports were not changed or run.

## Previous Product Version

`v0.7`

## New Product Version

`v0.8`

`v0.8` means Recommendation Loop Acceptance for controlled personal MVP runtime.

`v0.8` does not mean:

- recommendation planner quality is validated;
- all recommendation categories are refreshed;
- public/friends readiness;
- weak metrics are upgraded.

## Acceptance Basis

Promotion is based on the completed WP-016 chain:

- WP-016A Recommendation Loop Diagnosis.
- WP-016B Recommendation Legacy Refresh Repair.
- WP-016C Controlled Recommendation Refresh.
- WP-016D Runtime Recommendation Loop Acceptance: `PASS_WITH_WARNINGS`, loop armed.
- WP-016E failed safely due shell `TMPDIR`.
- WP-016E2 fixed `TMPDIR` and reached `no_new`.
- WP-016E3 imported real Competitive Dust2 match `#72` but evaluation did not trigger.
- WP-016E4 repaired targeted post-import evaluation and evaluated match `#72`.

Accepted facts:

- old survival recommendation `#1` is archived and preserved;
- active survival recommendation `#5` is confidence-aware;
- recommendation `#5` baseline ids are playable exact-date demo rows;
- recommendation `#5` baseline has `confidence.date_window` and `confidence.metrics`;
- fresh real match `#72` exists with `source=demo`, `map=de_dust2`, exact date via `steam_gc_match_time`, and persisted parser artifacts;
- evaluation `#76` exists with `recommendation_id=5`, `match_id=72`, `status=green`, `score=90`, and `evidence_json.metric_confidence`;
- progress updated to `completed_matches=1`, `needs_refresh=false`, `accepted_for_hard_progress=true`;
- legacy recommendations `#1`, `#3` and `#4` did not receive new evaluations;
- targeted tests passed in WP-016E4;
- full tests passed in WP-016E4;
- ruff passed in WP-016E4;
- service restart was clean in WP-016E4;
- no schema change;
- no persistent report generation;
- no DB reset/resync.

## Exact Proven Loop

```text
recommendation #5
  -> real playable exact-date Dust2 match #72
  -> evaluation #76 with metric_confidence
  -> progress completed_matches=1
```

## Recommendation #5 State

- id: `5`;
- category: `survival`;
- status: `active`;
- `needs_refresh=false`;
- `accepted_for_hard_progress=true`;
- baseline ids: playable exact-date `demo` rows `23-36,70`;
- baseline confidence: `confidence.date_window` present and `confidence.metrics` present;
- target metrics are derived from real baseline values and do not use `need data` placeholders.

## Match #72 State

- id: `72`;
- source: `demo`;
- map: `de_dust2`;
- exact date source: `steam_gc_match_time`;
- parser artifacts: persisted;
- retained demo file: not deleted or moved by WP-016F.

## Evaluation #76 State

- id: `76`;
- recommendation_id: `5`;
- match_id: `72`;
- status: `green`;
- score: `90`;
- `evidence_json.metric_confidence`: present;
- duplicate recommendation/match evaluation: none reported in WP-016E4.

## Progress State

- recommendation_id: `5`;
- completed_matches: `1`;
- needs_refresh: `false`;
- accepted_for_hard_progress: `true`;
- progress score after one match remains low because the target period is `10` matches.

## Warnings Carried Forward

- Active `grenades #3` and `map #4` remain legacy/`needs_refresh` and are not accepted for hard progress.
- Progress summary wording after one green evaluation is still rough: it may say the goal is failing because `progress_score` is low after `1/10` target matches. This is a UX/calibration warning, not a loop blocker.
- Authenticated browser UI was not directly inspected by Codex because no authenticated session was available.
- Weak metrics remain weak and caveated.
- Persistent report generation acceptance remains deferred because it mutates DB.
- `data/uploads` and `data/tmp` remain on root filesystem; storage guards remain required.
- Recommendation planner / verified top problem remains out of scope.

## Files Changed

- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_CONTROL.md`
- `docs/project_management/VERSION_ROADMAP.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/audit/WP_016F_PROMOTE_RECOMMENDATION_LOOP_TO_V0_8_REPORT.md`

## DB SHA

```text
36ccd84dc5c695af1c75a74f8d1059ade68a2a0355bb43aca1a7b473dd68f320  data/cs2_coach.db
```

## Production Safety

- Production DB touched: no.
- Production files touched: no production demo/upload/temp files touched; documentation files changed only.
- Live import/parser run: no.
- Live Steam/Valve import run: no.
- Demo downloaded: no.
- Parser job run: no.
- Persistent report generated: no.
- Schema changed: no.
- Runtime code changed: no.
- Tests changed: no.
- Commit made: no.

## Next Roadmap Accepted

- `v0.9` - Real Data Onboarding / Bulk Demo Usage.
- `v0.10` - Coach Quality Calibration.
- `v0.11` - Personal Daily Use UX.
- `v0.12` - Deployment / Backup / Storage Hardening.
- `v1.0` - Personal MVP Lock.

## Next Recommended WP

`WP-017A Roadmap v0.9-v1.0 Planning / Real Data Onboarding Diagnosis`
