# Version Roadmap

Last updated: 2026-07-04.

This is the roadmap control view for versions after WP-011C. It links product versions to work packages, guardians and acceptance evidence. `docs/PROJECT_CONTROL.md` remains the top source of truth; this file owns the version-to-WP roadmap table.

## Current Position

- Current Product Version: `v0.7`
- Current status: WP-016 recommendation loop acceptance in progress after controlled survival refresh.
- Next active target: `v0.8`
- Next active WP: `WP-016 Recommendation Loop Acceptance`

## Roadmap

| Version | Title | WP | Status | Purpose | Primary Guardians |
|---|---|---|---|---|---|
| `v0.4.1` | Runtime/Auth Emergency Repair | bugfix lane / evidence debt | done manually | Runtime/auth repair and operational freshness after the `/coach` stale-process incident. | `RUNTIME_GUARDIAN`, `DB_GUARDIAN`, `PM_ORCHESTRATOR` |
| `v0.4.2` | DB Contamination Guardrails | `WP-012` | completed | Prevent accidental production DB contamination from tests, imports, jobs, migrations and smoke checks. | `DB_GUARDIAN`, `TEST_GUARDIAN`, `IMPORT_GUARDIAN`, `RUNTIME_GUARDIAN` |
| `v0.5` | Personal MVP Runtime Acceptance | `WP-013` | completed / `PASS_WITH_WARNINGS` | Accept login/logout, dashboard, matches, `/coach`, reports and clean logs with no hidden live jobs. | `RUNTIME_GUARDIAN`, `UI_COACH_GUARDIAN`, `TEST_GUARDIAN` |
| `v0.6` | Import Acceptance | `WP-014` | completed / `PASS_WITH_WARNINGS` | Accept Steam/import/demo/matches/import_jobs/duplicates/errors without live-job ambiguity. | `IMPORT_GUARDIAN`, `DB_GUARDIAN`, `TEST_GUARDIAN` |
| `v0.7` | Metrics Correctness | `WP-015` | completed / `PASS_WITH_WARNINGS` | Establish golden fixtures, trusted metrics, exact-date window gating and explicit weak metric labels. | `METRICS_GUARDIAN`, `TEST_GUARDIAN`, `IMPORT_GUARDIAN` |
| `v0.8` | Recommendation Loop Acceptance | `WP-016` | in progress | Accept recommendation -> next match -> evaluation -> progress as a coherent coach loop. WP-016B added legacy detection/refresh foundation and WP-016C refreshed survival; runtime loop acceptance is pending. | `METRICS_GUARDIAN`, `UI_COACH_GUARDIAN`, `TEST_GUARDIAN` |
| `v0.9` | Personal Beta | `WP-017` | planned | Stable personal usage across real sessions on controlled VPS. | `PM_ORCHESTRATOR`, `RUNTIME_GUARDIAN`, `DB_GUARDIAN`, `TEST_GUARDIAN` |
| `v1.0` | Trusted MVP | `WP-018` | planned | Core loop trusted enough for serious personal use and demo. | all guardians |

## Version Rules

- A version is not accepted by docs alone. It needs WP evidence in `docs/audit/`, required checks and explicit exit criteria.
- A version may be `PASS_WITH_WARNINGS` only when warnings are named, bounded and carried into the next WP.
- Product features must not move ahead of DB/runtime/test safety gates.
- Historical stage docs remain evidence, but future planning should use `WORK_PACKAGE_BACKLOG.md` and `ACCEPTANCE_MATRIX.md`.

## Evidence Links

- WP backlog: `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- Acceptance matrix: `docs/project_management/ACCEPTANCE_MATRIX.md`
- Docs map: `docs/project_management/DOCS_MAP.md`
- Gate script: `scripts/project_gate.py`
- Project handoff: `docs/HANDOFF.md`
