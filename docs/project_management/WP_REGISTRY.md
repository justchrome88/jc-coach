# WP Registry

Last updated: 2026-07-05.

This is the canonical work-package registry for JC Coach. It preserves WP
history and prevents silent WP ID reuse, skipped prerequisites or promotion
drift. `docs/PROJECT_CONTROL.md`, `docs/HANDOFF.md`,
`docs/CURRENT_STATUS.md`, `WORK_PACKAGE_BACKLOG.md`,
`ACCEPTANCE_MATRIX.md` and `VERSION_ROADMAP.md` must stay aligned with this
registry.

## Governance Rules

- `AGENTS.md` must exist before WP work starts.
- `docs/project_management/WP_REGISTRY.md` must exist before roadmap or
  promotion work starts.
- WP IDs must not be silently reused for a different objective.
- If a planned WP is skipped, it must be marked `deferred` or `superseded` here
  with the reason and the accepting report.
- Promotion WPs must verify all registry prerequisites before promotion.
- `v0.9` promotion is blocked until `WP-017I` and `WP-017J` are completed or
  explicitly deferred with a documented accepted limitation.
- Historical emergency repair WPs remain in the registry. They were inserted
  because the Steam-path automatic recommendation evaluation trigger became a
  blocker during WP-017.

## Status Values

Allowed statuses: `planned`, `in_progress`, `done`, `blocked`, `deferred`,
`superseded`.

## WP-017 Canonical Order

| WP ID | Title | Version target | Status | Report path | Dependencies | Notes / warnings |
|---|---|---|---|---|---|---|
| `WP-017A` | Real Data Onboarding / Bulk Demo Usage Diagnosis | `v0.9` | `done` | `docs/audit/WP_017A_REAL_DATA_ONBOARDING_DIAGNOSIS.md` | `v0.8` promoted | Diagnosed storage/import/data state; match mode remained unknown. |
| `WP-017B` | Controlled Bulk Import Plan / Guard Settings | `v0.9` | `done` | `docs/audit/WP_017B_CONTROLLED_BULK_IMPORT_PLAN_REPORT.md` | `WP-017A` | Planned one-demo cap runbook; no live work. |
| `WP-017C` | First Controlled Bulk Import Batch / No-New Path | `v0.9` | `done` | `docs/audit/WP_017C_FIRST_CONTROLLED_BULK_IMPORT_BATCH_REPORT.md` | `WP-017B`, explicit live authorization | One authorized `steam_import_all` no-new path; no demo/parser/evaluation. |
| `WP-017C2` | Controlled Import After New Match / One-Demo Batch-Cap Path | `v0.9` | `done` | `docs/audit/WP_017C2_CONTROLLED_IMPORT_AFTER_NEW_MATCH_REPORT.md` | `WP-017C`, new real match, explicit live authorization | Imported match `#75`; manual evaluation exposed auto-evaluation blocker; cap stayed `1`. |
| `WP-017D` | Post-Batch Acceptance + Auto-Evaluation Trigger Diagnosis | `v0.9` | `done` | `docs/audit/WP_017D_POST_BATCH_ACCEPTANCE_AND_EVALUATION_TRIGGER_DIAGNOSIS.md` | `WP-017C2` | Accepted batch evidence with repair required; blocked pending `#73` and cap raise. |
| `WP-017E` | Auto-Evaluation Trigger Repair for Steam Batch Import Path | `v0.9` | `done` | `docs/audit/WP_017E_AUTO_EVALUATION_TRIGGER_REPAIR_REPORT.md` | `WP-017D` | Emergency repair WP inserted because automatic evaluation was a blocker. |
| `WP-017F` | Controlled Pending Share Code `#73` Import | `v0.9` | `done` | `docs/audit/WP_017F_CONTROLLED_PENDING_73_IMPORT_REPORT.md` | `WP-017E`, explicit live authorization | Proved repaired path on match `#76`; targeted path lacks parent job metadata. |
| `WP-017G` | Post-Batch Data Integrity Acceptance | `v0.9` | `done` | `docs/audit/WP_017G_POST_BATCH_DATA_INTEGRITY_ACCEPTANCE_REPORT.md` | `WP-017F` | Data integrity accepted with warnings; match mode still provenance-only/unknown. |
| `WP-017H` | Post-Batch Performance Acceptance | `v0.9` | `done` | `docs/audit/WP_017H_POST_BATCH_PERFORMANCE_ACCEPTANCE_REPORT.md` | `WP-017G` | Performance accepted with warnings; authenticated browser timing unavailable. |
| `WP-017I0` | Add Root `AGENTS.md` Project Contract | `v0.9` | `done` | `docs/audit/WP_017I0_ADD_ROOT_AGENTS_PROJECT_CONTRACT_REPORT.md` | `WP-017H` | Added root Codex contract; did not promote `v0.9`. |
| `WP-017R` | Roadmap / WP Registry Governance Repair | `v0.9` | `in_progress` | `docs/audit/WP_017R_ROADMAP_WP_REGISTRY_GOVERNANCE_REPAIR_REPORT.md` | `WP-017I0` | Current governance repair; creates this registry and blocks promotion until match mode WPs are resolved. |
| `WP-017I` | Match Mode Classification Diagnosis | `v0.9` | `planned` | TBD | `WP-017R` | Diagnose whether Premier/Competitive/Wingman can be recovered from reliable persisted metadata or external evidence. No live import/parser by default. |
| `WP-017J` | Match Mode Classification Repair / Labels, Or Explicit Deferral | `v0.9` | `planned` | TBD | `WP-017I` | Repair labels if recoverable, or document accepted limitation/deferral. Required before promotion unless explicitly deferred. |
| `WP-017K` | Real Data Onboarding Promotion to `v0.9` | `v0.9` | `planned` | TBD | `WP-017G`, `WP-017H`, `WP-017I`, `WP-017J` or documented deferral | Promotion WP only. Must not raise cap, delete demos, change schema or claim friends/public readiness. |

## Current Promotion Gate

`v0.9` promotion is not allowed now.

Required before `WP-017K` can promote:

- `WP-017I` completed: match mode classification diagnosed.
- `WP-017J` completed or explicitly deferred: mode labels repaired if
  recoverable, or limitation accepted in writing.
- Existing WP-017G/H warnings carried forward.
- Cap remains `1` unless a separate explicit cap-change WP authorizes a change.

## Future Version Registry

| WP ID | Title | Version target | Status | Report path | Dependencies | Notes / warnings |
|---|---|---|---|---|---|---|
| `WP-018` | Coach Quality Calibration | `v0.10` | `planned` | TBD | `WP-017K` promotion or explicit `v0.9` block decision | Calibrate coach claims, progress scoring and weak-metric caveats. |
| `WP-019` | Personal Daily Use UX | `v0.11` | `planned` | TBD | `WP-018` | Daily owner workflow polish without friends/public claims. |
| `WP-020` | Deployment / Backup / Storage Hardening | `v0.12` | `planned` | TBD | `WP-019` | VPS operation, backup/restore and storage hardening. |
| `WP-021` | Personal MVP Lock | `v1.0` | `planned` | TBD | `WP-020` | Controlled personal MVP lock; public/friends readiness remains separate. |
