# Version Roadmap

Last updated: 2026-07-05.

This is the roadmap control view for versions after WP-011C. It links product versions to work packages, guardians and acceptance evidence. `docs/PROJECT_CONTROL.md` remains the top source of truth; this file owns the version-to-WP roadmap table.

## Current Position

- Current Product Version: `v0.8`
- Current status: v0.9 Real Data Onboarding / Bulk Demo Usage is in progress; WP-017A diagnosed the baseline, WP-017B planned the first controlled batch runbook, WP-017C completed one no-new controlled batch, WP-017C2 imported/parsed/evaluated one new playable exact-date demo under cap `1`, WP-017D required a repair for the automatic Steam-path evaluation trigger, WP-017E repaired that trigger in code/tests, WP-017F proved it on pending `#73`, WP-017G accepted post-batch data integrity with warnings, WP-017H accepted performance with warnings, WP-017I0 added root `AGENTS.md`, WP-017R repaired roadmap/WP registry governance, and WP-017I diagnosed exact playlist mode as unrecoverable from persisted data.
- Next active target: `v0.9`
- Next active WP: `WP-017J Match Mode Classification Repair / Labels, Or Explicit Deferral`

## Roadmap

| Version | Title | WP | Status | Purpose | Primary Guardians |
|---|---|---|---|---|---|
| `v0.4.1` | Runtime/Auth Emergency Repair | bugfix lane / evidence debt | done manually | Runtime/auth repair and operational freshness after the `/coach` stale-process incident. | `RUNTIME_GUARDIAN`, `DB_GUARDIAN`, `PM_ORCHESTRATOR` |
| `v0.4.2` | DB Contamination Guardrails | `WP-012` | completed | Prevent accidental production DB contamination from tests, imports, jobs, migrations and smoke checks. | `DB_GUARDIAN`, `TEST_GUARDIAN`, `IMPORT_GUARDIAN`, `RUNTIME_GUARDIAN` |
| `v0.5` | Personal MVP Runtime Acceptance | `WP-013` | completed / `PASS_WITH_WARNINGS` | Accept login/logout, dashboard, matches, `/coach`, reports and clean logs with no hidden live jobs. | `RUNTIME_GUARDIAN`, `UI_COACH_GUARDIAN`, `TEST_GUARDIAN` |
| `v0.6` | Import Acceptance | `WP-014` | completed / `PASS_WITH_WARNINGS` | Accept Steam/import/demo/matches/import_jobs/duplicates/errors without live-job ambiguity. | `IMPORT_GUARDIAN`, `DB_GUARDIAN`, `TEST_GUARDIAN` |
| `v0.7` | Metrics Correctness | `WP-015` | completed / `PASS_WITH_WARNINGS` | Establish golden fixtures, trusted metrics, exact-date window gating and explicit weak metric labels. | `METRICS_GUARDIAN`, `TEST_GUARDIAN`, `IMPORT_GUARDIAN` |
| `v0.8` | Recommendation Loop Acceptance | `WP-016` | completed / promoted | Accept recommendation -> next match -> evaluation -> progress as a coherent controlled personal coach loop. Proven loop: `#5 -> #72 -> #76 -> completed_matches=1`. Planner quality, all-category refresh and friends/public readiness remain out of scope. | `METRICS_GUARDIAN`, `UI_COACH_GUARDIAN`, `TEST_GUARDIAN`, `DB_GUARDIAN` |
| `v0.9` | Real Data Onboarding / Bulk Demo Usage | `WP-017A`-`WP-017K` | in progress; WP-017A diagnosed, WP-017B planned, WP-017C completed no-new, WP-017C2 completed one-demo import/evaluation with batch-cap warning, WP-017D accepted with repair required, WP-017E repaired the auto-evaluation trigger, WP-017F proved it live on pending `#73`, WP-017G accepted data integrity with warnings, WP-017H accepted performance with warnings, WP-017I0 added root `AGENTS.md`, WP-017R repaired registry governance, WP-017I diagnosed mode classification | Onboard more real matches/demos through controlled one-demo batches with storage, DB, parser, recommendation and runtime evidence. WP-017G accepted 76 total matches, 22 playable demos, exact-date matches `#75/#76`, parser artifacts `#50/#51`, and recommendation `#5` progress `3/10`; WP-017H accepted sub-2s read-only helper performance with warnings. Exact playlist mode is not recoverable from persisted data; promotion is blocked until WP-017J repairs labels or explicitly defers playlist classification, then WP-017K may decide promotion. | `PM_ORCHESTRATOR`, `IMPORT_GUARDIAN`, `DB_GUARDIAN`, `RUNTIME_GUARDIAN`, `TEST_GUARDIAN`, `METRICS_GUARDIAN` |
| `v0.10` | Coach Quality Calibration | `WP-018` | planned | Calibrate recommendation quality, progress wording, coach claims and weak-metric caveats against accepted evidence. | `METRICS_GUARDIAN`, `UI_COACH_GUARDIAN`, `TEST_GUARDIAN`, `PM_ORCHESTRATOR` |
| `v0.11` | Personal Daily Use UX | `WP-019` | planned | Make daily personal workflows clear, repeatable and low-friction without claiming friends/public readiness. | `UI_COACH_GUARDIAN`, `RUNTIME_GUARDIAN`, `TEST_GUARDIAN` |
| `v0.12` | Deployment / Backup / Storage Hardening | `WP-020` | planned | Harden VPS operation, backup/restore evidence, storage layout and recovery before MVP lock. | `RUNTIME_GUARDIAN`, `DB_GUARDIAN`, `IMPORT_GUARDIAN`, `PM_ORCHESTRATOR` |
| `v1.0` | Personal MVP Lock | `WP-021` | planned | Lock the controlled personal MVP scope and evidence for serious personal use. | all guardians |

## Version Rules

- A version is not accepted by docs alone. It needs WP evidence in `docs/audit/`, required checks and explicit exit criteria.
- A version may be `PASS_WITH_WARNINGS` only when warnings are named, bounded and carried into the next WP.
- Product features must not move ahead of DB/runtime/test safety gates.
- Historical stage docs remain evidence, but future planning should use `WORK_PACKAGE_BACKLOG.md` and `ACCEPTANCE_MATRIX.md`.
- WP IDs must not be silently reused. Planned WPs that are skipped must be marked `deferred` or `superseded` with a reason in `docs/project_management/WP_REGISTRY.md`.
- Promotion WPs must verify registry prerequisites before changing product version.

## Evidence Links

- WP backlog: `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- WP registry: `docs/project_management/WP_REGISTRY.md`
- Acceptance matrix: `docs/project_management/ACCEPTANCE_MATRIX.md`
- Docs map: `docs/project_management/DOCS_MAP.md`
- Gate script: `scripts/project_gate.py`
- Project handoff: `docs/HANDOFF.md`
