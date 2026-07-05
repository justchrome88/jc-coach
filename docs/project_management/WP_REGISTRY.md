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
- `v0.9` promotion must verify `WP-017I` and `WP-017J` evidence. `WP-017J`
  accepted explicit deferral, so promotion may proceed only through `WP-017K`
  with the documented limitation carried forward.
- Historical emergency repair WPs remain in the registry. They were inserted
  because the Steam-path automatic recommendation evaluation trigger became a
  blocker during WP-017.
- `docs/audit/WP_018_DOCUMENTATION_GOVERNANCE_AUDIT_REPORT.md` is an
  out-of-band governance audit evidence file. It does not consume or replace
  the planned `WP-018` product work-package ID.

## Status Values

Allowed statuses: `planned`, `active`, `in_progress`, `done`, `blocked`,
`deferred`, `failed`, `superseded`, `out-of-band evidence`.

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
| `WP-017R` | Roadmap / WP Registry Governance Repair | `v0.9` | `done` | `docs/audit/WP_017R_ROADMAP_WP_REGISTRY_GOVERNANCE_REPAIR_REPORT.md` | `WP-017I0` | Created registry and blocked promotion until match mode WPs are resolved. |
| `WP-017I` | Match Mode Classification Diagnosis | `v0.9` | `done` | `docs/audit/WP_017I_MATCH_MODE_CLASSIFICATION_DIAGNOSIS_REPORT.md` | `WP-017R` | Persisted data cannot distinguish exact playlist mode; current rows should remain playlist `unknown`. |
| `WP-017J` | Match Mode Explicit Deferral / Unknown Labels | `v0.9` | `done` | `docs/audit/WP_017J_MATCH_MODE_EXPLICIT_DEFERRAL_REPORT.md` | `WP-017I` | Explicit deferral accepted: `v0.9` will not include exact playlist classification. Use `mode_unknown`, `provenance_demo`, `provenance_valve_matchmaking` and `exact_date_source=steam_gc_match_time`; do not claim Premier/Competitive/Wingman/Casual/Deathmatch/FACEIT/custom without future reliable metadata. |
| `WP-017S` | Documentation Governance Entrypoint Repair | `v0.9` | `done` | `docs/audit/WP_017S_GOVERNANCE_ENTRYPOINT_REPAIR_REPORT.md` | `WP-017J`, out-of-band governance audit evidence | Service governance repair before promotion lane continues; does not consume planned `WP-018`. |
| `WP-017T` | Compact Current Status and Handoff | `v0.9` | `done` | `docs/audit/WP_017T_COMPACT_CURRENT_STATUS_HANDOFF_REPORT.md` | `WP-017S` | Governance/documentation pass that compresses Hot current-state docs before promotion review; no product logic, DB, service or WP-018 product block changes. |
| `WP-017U` | Project Operating Protocol and Master WP Checklist | `v0.9` | `done` | `docs/audit/WP_017U_PROJECT_OPERATING_PROTOCOL_REPORT.md` | `WP-017T` | Governance/documentation pass that adds the operating protocol and human master WP checklist before promotion review; no product logic, DB, service or WP-018 product block changes. |
| `WP-017V` | Repo-Native Agent Workflow and Docs Steward | `v0.9` | `done` | `docs/audit/WP_017V_AGENT_WORKFLOW_REPORT.md` | `WP-017U` | Governance/documentation pass that adds repo-native WP role workflow and Documentation Steward / Docs Currency Agent; no product logic, DB, service or WP-018 product block changes. |
| `WP-017W` | Task Type Profiles and Prompt Contract | `v0.9` | `done` | `docs/audit/WP_017W_TASK_TYPE_PROFILES_PROMPT_CONTRACT_REPORT.md` | `WP-017V` | Governance/documentation pass that adds task type routing, role invocation shortcuts and Task Card prompt contract; no product logic, DB, service or WP-018 product block changes. |
| `WP-017X` | Legacy Documentation Currency Snapshot | `v0.9` | `done` | `docs/audit/WP_017X_LEGACY_DOCUMENTATION_CURRENCY_SNAPSHOT_REPORT.md` | `WP-017W` | Documentation Steward snapshot of legacy docs and conservative cleanup/deprecation plan; inspection only, no file moves/deletes/archive cleanup, no product logic, DB, service or WP-018 product block changes. |
| `WP-017Y` | No-Risk Legacy Docs Pointer Cleanup | `v0.9` | `done` | `docs/audit/WP_017Y_LEGACY_DOCS_POINTER_CLEANUP_REPORT.md` | `WP-017X` | Documentation/governance pass that adds no-risk status headers and pointer cleanup to legacy docs; no file moves/deletes/archive cleanup, no product logic, DB, service or WP-018 product block changes. |
| `WP-017K` | Real Data Onboarding Promotion to `v0.9` | `v0.9` | `planned` | TBD | `WP-017G`, `WP-017H`, `WP-017I`, `WP-017J` or documented deferral, `WP-017S`, `WP-017T`, `WP-017U`, `WP-017V`, `WP-017W`, `WP-017X`, `WP-017Y` | Promotion WP only. Must not raise cap, delete demos, change schema or claim friends/public readiness. |

## Current Promotion Gate

`v0.9` promotion is not completed now, but `WP-017K` may start.

Required before `WP-017K` can promote:

- `WP-017I` completed: match mode classification diagnosed.
- `WP-017J` completed with explicit deferral accepted: Match playlist mode is
  not accepted as exact in `v0.9`. Current persisted data distinguishes
  parser/import provenance (`demo`) and generic Valve share-code provenance
  (`Valve Matchmaking`), but it does not reliably distinguish Premier,
  Competitive, Wingman, Casual, Deathmatch, FACEIT or custom modes. No
  playlist-specific claims, filters or recommendations are accepted in `v0.9`
  unless future WPs capture reliable mode metadata.
- Existing WP-017G/H warnings carried forward.
- `WP-017S` completed: governance entrypoints repaired and `WP-018` audit
  naming conflict documented as out-of-band evidence.
- `WP-017T` completed: active current-state and handoff docs compressed so
  future prompts can stay short while current project truth remains in-repo.
- `WP-017U` completed: practical project operating protocol and human master WP
  checklist exist before promotion review.
- `WP-017V` completed: repo-native WP role workflow and Documentation Steward
  checks exist as Warm governance references before promotion review.
- `WP-017W` completed: task type profiles, role invocation shortcuts and Task
  Card prompt contract exist as Warm governance references before promotion
  review.
- `WP-017X` completed: legacy documentation currency snapshot exists before
  promotion review; no physical cleanup was performed.
- `WP-017Y` completed: no-risk legacy pointer cleanup added status headers and
  safer source-of-truth pointers; no physical cleanup was performed.
- Cap remains `1` unless a separate explicit cap-change WP authorizes a change.

## Future Version Registry

| WP ID | Title | Version target | Status | Report path | Dependencies | Notes / warnings |
|---|---|---|---|---|---|---|
| `WP-018` | Coach Quality Calibration | `v0.10` | `planned` | TBD | `WP-017K` promotion or explicit `v0.9` block decision | Calibrate coach claims, progress scoring and weak-metric caveats. |
| `WP-019` | Personal Daily Use UX | `v0.11` | `planned` | TBD | `WP-018` | Daily owner workflow polish without friends/public claims. |
| `WP-020` | Deployment / Backup / Storage Hardening | `v0.12` | `planned` | TBD | `WP-019` | VPS operation, backup/restore and storage hardening. |
| `WP-021` | Personal MVP Lock | `v1.0` | `planned` | TBD | `WP-020` | Controlled personal MVP lock; public/friends readiness remains separate. |
