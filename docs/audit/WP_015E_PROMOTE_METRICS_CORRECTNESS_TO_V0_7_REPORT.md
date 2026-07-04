# WP-015E Promote Metrics Correctness To v0.7 Report

Date: 2026-07-04

## RESULT: PROMOTED

WP-015 Metrics Correctness is promoted to `v0.7` for controlled personal MVP runtime.

This is a documentation/status promotion only. No runtime code, tests, schema, production DB data, production demo files, live Steam import, demo download or parser job was changed or run.

## Previous Product Version

`v0.6`

## New Product Version

`v0.7`

`v0.7` means Metrics Correctness guardrails are accepted for personal MVP runtime.

`v0.7` does not mean:

- friends/public readiness;
- all metric formulas are externally validated;
- weak parser metrics are upgraded;
- recommendation loop acceptance is complete.

## Acceptance Basis

Promotion is based on:

- WP-015A Match Date Truth Reconciliation Diagnosis.
- WP-015A1 controlled date-truth repair.
- WP-015B Metrics Correctness Diagnosis.
- WP-015C Metrics Confidence and Date-Window Gating Repair.
- WP-015C-PERF Performance Diagnosis.
- WP-015C1 Metrics Performance Repair.
- WP-015D Runtime Metrics Acceptance: `PASS_WITH_WARNINGS`.

Accepted behavior:

- confidence/date-window gating implemented;
- unsupported metrics suppressed or relabelled;
- approximate rows excluded from exact recent/trend/form windows;
- recommendation baseline/evaluation carries confidence for new/rebuilt data;
- AI payload includes confidence metadata;
- dashboard/stats/coach performance repaired:
  - dashboard builder around `166 ms`;
  - stats builder around `312 ms`;
  - coach builder around `581 ms`;
  - AI payload around `506 ms`;
- service restart clean;
- DB SHA unchanged;
- no production DB mutation;
- no production files touched;
- no live import/parser jobs;
- no schema change.

## Warnings Carried Forward

- Direct post-restart authenticated browser timings were not captured by Codex because no authenticated session was available.
- Existing persisted recommendation baseline `#1` lacks stored confidence metadata until explicitly refreshed/rebuilt in a future WP.
- Persistent report generation acceptance is deferred because report generation mutates DB.
- `/coach` artifact overview is currently acceptable but still loads many artifact ORM rows and should be optimized before the demo corpus grows substantially.
- Weak metrics remain weak; `v0.7` verifies labels/gating, not formula truth upgrades.
- `ImportJob.status` is still coarse; import truth primarily lives in `result_json`.
- uploads/tmp remain on root filesystem; dedicated storage remains recommended.
- Friends/public readiness remains blocked by broader security, ownership, observability, backup and release gates.

## Files Changed

- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_CONTROL.md`
- `docs/project_management/VERSION_ROADMAP.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/audit/WP_015E_PROMOTE_METRICS_CORRECTNESS_TO_V0_7_REPORT.md`

## DB SHA

```text
8811b08c3e15348ab60ee022887c90ecbe4a17b4bef8ea5d035c083d8f2b6f1c  data/cs2_coach.db
```

## Production Safety

- Production DB touched: no.
- Production files touched: no.
- Live import/parser run: no.
- Schema changed: no.
- Runtime code changed: no.
- Tests changed: no.
- Commit made: no.

## Next Recommended WP

`WP-016 Recommendation Loop Acceptance`

Target version: `v0.8`.

Focus: accept recommendation -> next match -> evaluation -> progress as a coherent loop using the accepted `v0.7` metric confidence and date-window rules.

