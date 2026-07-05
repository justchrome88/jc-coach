# Docs Map

Last updated: 2026-07-05.

This map connects project docs to the Project OS layer, architecture/product
layers, guardian ownership, work packages and freshness risk. Current operating
hierarchy starts with `AGENTS.md`, `docs/CURRENT_STATUS.md` and
`docs/project_management/WP_REGISTRY.md`.

For human navigation by category, start with `docs/README.md` and `docs/project_management/DOCS_INDEX.md`.

## Context Policy

Per-task Hot context:

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/project_management/WP_REGISTRY.md`

New-session Hot context additionally includes `docs/HANDOFF.md`.

Warm context is task-domain specific. Cold context includes old audit reports,
stage reports, old prompts, `docs/tasks/*`, `instructions/*`, old
roadmap/version docs and generated data reports. Cold context is evidence and
must not override Hot context.

`docs/project_management/PROJECT_OPERATING_PROTOCOL.md` and
`docs/project_management/MASTER_WP_CHECKLIST.md` are not per-task Hot context.
`docs/project_management/AGENT_WORKFLOW.md` is also Warm governance context,
not per-task Hot context. Read them only when governance, planning, WP role
workflow or audit scope requires them.

## Project OS Layer

| Document | Role | Guardian | WP links | Status |
|---|---|---|---|---|
| `AGENTS.md` | Only root Codex operating contract. | `PM_ORCHESTRATOR` | all WPs | Hot source-of-truth |
| `AGENT.md` | Superseded pointer to `AGENTS.md`. | `PM_ORCHESTRATOR` | historical | superseded / not active |
| `docs/PROJECT_CONTROL.md` | Legacy project control file below current Hot context. | `PM_ORCHESTRATOR` | all WPs | supporting source-of-truth |
| `docs/README.md` | Human documentation entrypoint. | `PM_ORCHESTRATOR` | all WPs | navigation index |
| `docs/PROJECT_OS.md` | Historical/superseded entrypoint; use Hot context instead. | `PM_ORCHESTRATOR` | historical | superseded / not current state |
| `docs/HANDOFF.md` | Current continuation state. | `PM_ORCHESTRATOR` | active/next WP | source-of-truth, must stay current |
| `docs/PROJECT_GOVERNANCE.md` | Versioning, WP gates, roles, safety policy. | `PM_ORCHESTRATOR` | all WPs | Warm governance reference |
| `docs/project_management/PROJECT_OPERATING_PROTOCOL.md` | Practical operating protocol for roles, source-of-truth hierarchy, WP lifecycle, blockers, reports, commits and chat policy. | `PM_ORCHESTRATOR` | all WPs | Warm governance reference |
| `docs/project_management/AGENT_WORKFLOW.md` | Repo-native WP role workflow for PM, Implementation, QA and Documentation Steward checks. | `PM_ORCHESTRATOR` | all WPs | Warm governance reference; not per-task Hot context |
| `docs/project_management/VERSION_ROADMAP.md` | Version-to-WP roadmap. | `PM_ORCHESTRATOR` | WP-012..WP-018 | source-of-truth for planned version sequence |
| `docs/project_management/WORK_PACKAGE_BACKLOG.md` | WP objectives, guardians and exit criteria. | `PM_ORCHESTRATOR` | WP-012..WP-018 | source-of-truth for backlog wiring |
| `docs/project_management/ACCEPTANCE_MATRIX.md` | Feature acceptance map. | `PM_ORCHESTRATOR`, domain guardians | WP-012..WP-018 | source-of-truth for acceptance wiring |
| `docs/project_management/MASTER_WP_CHECKLIST.md` | Human-readable full WP campaign map. | `PM_ORCHESTRATOR` | WP-011D..WP-021 | Warm/Cold planning map; registry wins for status/dependencies/report paths |
| `docs/project_management/DOCS_MAP.md` | Documentation ownership map. | `PM_ORCHESTRATOR` | all WPs | source-of-truth for docs wiring |
| `docs/project_management/DOCS_INDEX.md` | Human-readable documentation index. | `PM_ORCHESTRATOR` | all WPs | navigation index |

## Product Architecture Layer

| Document | Layer | Guardian | WP links | Status |
|---|---|---|---|---|
| `docs/ARCHITECTURE.md` | System shape and boundaries. | `RUNTIME_GUARDIAN`, `PM_ORCHESTRATOR` | WP-013..WP-018 | source-of-truth |
| `docs/SECURITY.md` | Auth/security readiness. | `DB_GUARDIAN`, `RUNTIME_GUARDIAN` | WP-012, WP-013, WP-017 | source-of-truth |
| `docs/METRICS.md` | Runtime metric truth contract. | `METRICS_GUARDIAN` | WP-015, WP-016 | source-of-truth |
| `docs/STEAM_IMPORT.md` | Steam import current truth. | `IMPORT_GUARDIAN` | WP-014 | source-of-truth |
| `docs/RECOMMENDATIONS.md` | Coach loop and recommendation rules. | `METRICS_GUARDIAN`, `UI_COACH_GUARDIAN` | WP-016 | source-of-truth |
| `docs/AI_COACH.md` | AI provider/output truth. | `METRICS_GUARDIAN` | WP-015, WP-016 | source-of-truth |
| `docs/TESTING.md` | Safe verification commands. | `TEST_GUARDIAN`, `DB_GUARDIAN` | all WPs | source-of-truth |
| `docs/BACKUP_RESTORE.md` | Backup/restore policy. | `DB_GUARDIAN` | WP-012, WP-017 | source-of-truth |
| `docs/DEPLOYMENT.md` | Deployment shape and gates. | `RUNTIME_GUARDIAN` | WP-013, WP-017 | source-of-truth |
| `docs/KNOWN_LIMITATIONS.md` | Known non-readiness areas. | `PM_ORCHESTRATOR` | WP-017, WP-018 | source-of-truth |

## Roadmap And Status

| Document | Role | Guardian | WP links | Status |
|---|---|---|---|---|
| `docs/CURRENT_STATUS.md` | Current product fact state. | `PM_ORCHESTRATOR` | active WP | source-of-truth |
| `docs/CURRENT_MILESTONE.md` | Historical/current hardening milestone detail. | `PM_ORCHESTRATOR` | stages 0-9, WP-012 context | source-of-truth for stage evidence, stale version-label risk |
| `docs/ROADMAP.md` | Ordered development overview. | `PM_ORCHESTRATOR` | roadmap WPs | source-of-truth but needs alignment with `VERSION_ROADMAP.md` |
| `docs/VERSION_MAP.md` | Version readiness map. | `PM_ORCHESTRATOR` | roadmap WPs | source-of-truth but stale legacy version labels exist |
| `docs/CHANGELOG.md` | Curated change history. | `PM_ORCHESTRATOR` | all completed WPs/stages | supporting |
| `docs/DECISIONS.md` | Current decisions. | `PM_ORCHESTRATOR` | all WPs | supporting |
| `docs/RELEASE_CHECKLIST.md` | Personal/friends/public gates. | `PM_ORCHESTRATOR`, `RUNTIME_GUARDIAN` | WP-017, WP-018 | source-of-truth for release checks |

## Supporting Domain Docs

| Document | Role | Guardian | WP links | Status |
|---|---|---|---|---|
| `docs/FEATURES_RU.md` | Implemented feature summary. | `PM_ORCHESTRATOR` | reference | supporting, stale risk |
| `docs/STEAM_IMPORT_ARCHITECTURE.md` | Deeper Steam architecture. | `IMPORT_GUARDIAN` | WP-014 | supporting |
| `docs/STEAM_MATCH_DATES_RU.md` | Steam match date policy. | `IMPORT_GUARDIAN` | WP-014 | supporting |
| `docs/DEMO_DEEP_PARSER_TZ_RU.md` | Parser requirements/context. | `IMPORT_GUARDIAN`, `METRICS_GUARDIAN` | WP-014, WP-015 | supporting |
| `docs/DEMO_STORAGE_TZ.md` | Demo storage lifecycle plan. | `IMPORT_GUARDIAN`, `DB_GUARDIAN` | WP-014, later storage WP | supporting |
| `docs/MIGRATIONS.md` | Migration discipline and copy-check policy. | `DB_GUARDIAN` | WP-012 | source-of-truth |
| `docs/PUBLIC_DEPLOYMENT_CHECKLIST.md` | Public deployment checklist. | `RUNTIME_GUARDIAN`, `PM_ORCHESTRATOR` | WP-017+ | supporting; blocked by security |

## Historical Or Stale-Risk Planning Docs

| Document | Role | Guardian | WP links | Status |
|---|---|---|---|---|
| `docs/PRODUCT_EXECUTION_STRATEGY.md` | Older product strategy. | `PM_ORCHESTRATOR` | reference only | stale risk / historical per deprecation plan |
| `docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md` | Older implementation plan. | `PM_ORCHESTRATOR` | reference only | stale risk / historical |
| `docs/NON_STOP_DEVELOPMENT_PROMPTS.md` | Prompt library. | `PM_ORCHESTRATOR` | none unless reactivated | stale risk / historical |
| `docs/AI_COACH_PROVIDER_ARCHITECTURE.md` | AI provider memo. | `METRICS_GUARDIAN` | WP-016+ | supporting/historical; canonical truth is `AI_COACH.md` |
| `docs/AI_RECOMMENDATIONS_AIM_EXECUTION_PLAN_RU.md` | Older AI/recommendation plan. | `METRICS_GUARDIAN` | reference only | stale risk / historical |
| `docs/COMPETITOR_FEATURE_MATRIX.md` | Market comparison. | `PM_ORCHESTRATOR` | later product planning | supporting/historical |
| `docs/FEATURE_ROADMAP_SCORING.md` | Feature scoring. | `PM_ORCHESTRATOR` | later planning | supporting/historical |
| `docs/METRICS_ROADMAP_SCORING_RU.md` | Metric wishlist/scoring. | `METRICS_GUARDIAN` | WP-015 reference | supporting/historical |
| `docs/feature_roadmap_scoring_ru.xlsx` | Spreadsheet source. | `PM_ORCHESTRATOR` | later planning | supporting artifact |
| `docs/metrics_roadmap_scoring_ru.xlsx` | Spreadsheet source. | `METRICS_GUARDIAN` | WP-015 reference | supporting artifact |

## Audit Docs

| Pattern / Document | Role | Guardian | WP links | Status |
|---|---|---|---|---|
| `docs/audit/STAGE_1_*` through `docs/audit/STAGE_9_*` | Stage implementation/review evidence. | relevant domain guardian + `PM_ORCHESTRATOR` | historical stages, evidence for WP-013..WP-016 | source evidence |
| `docs/audit/WP_011B_PROJECT_OS_IMPLEMENTATION_REPORT.md` | Project OS implementation evidence. | `PM_ORCHESTRATOR` | WP-011B | source evidence |
| `docs/audit/WP_011C_ROADMAP_DOCS_WIRING_REPORT.md` | Roadmap/docs wiring evidence. | `PM_ORCHESTRATOR` | WP-011C | source evidence |
| `docs/audit/WP_014A_STEAM_VALVE_IMPORT_DIAGNOSIS.md` | One-button Steam/Valve import diagnosis and `v0.6` repair criteria. | `IMPORT_GUARDIAN`, `DB_GUARDIAN`, `PM_ORCHESTRATOR` | WP-014 | source evidence |
| `docs/audit/BUGFIX_001_COACH_RUNTIME_FAILURE_DIAGNOSIS.md` | Runtime stale-process diagnosis. | `RUNTIME_GUARDIAN`, `UI_COACH_GUARDIAN` | v0.4.1, WP-013 | source evidence; formal repair audit still needed |
| `docs/audit/*_INVENTORY.md` | Domain inventories. | corresponding guardian | WP-012..WP-016 | source/supporting evidence |
| `docs/audit/DOCUMENT_CONFLICTS.md` | Conflict inventory. | `PM_ORCHESTRATOR` | docs cleanup | source evidence, stale version-label risk |
| `docs/audit/DOCUMENT_DEPRECATION_PLAN.md` | Historical doc policy. | `PM_ORCHESTRATOR` | docs cleanup | source-of-truth for deprecation |
| `docs/audit/FULL_PROJECT_AUDIT_*` | Full audits and draft tasks. | `PM_ORCHESTRATOR` | context for future WPs | supporting; may be stale after WP-011C |
| `docs/audit/CS2_AI_COACH_AUDIT_2026-07-02.md` | Earlier project audit. | `PM_ORCHESTRATOR` | reference | supporting/historical |

## Task Docs

| Pattern / Document | Role | Guardian | WP links | Status |
|---|---|---|---|---|
| `docs/tasks/STABILIZATION_STAGE_0_*` through `docs/tasks/STABILIZATION_STAGE_9_*` | Historical stage task prompts. | corresponding guardian + `PM_ORCHESTRATOR` | stages 0-9 | source evidence for what was asked; not active roadmap |
| `docs/tasks/FULL_PROJECT_AUDIT_AFTER_DOCS_TASK.md` | Earlier audit task. | `PM_ORCHESTRATOR` | docs cleanup | supporting/historical |
| `docs/tasks/INSTRUCTIONS_CONSOLIDATION_TASK.md` | Earlier consolidation task. | `PM_ORCHESTRATOR` | docs cleanup | supporting/historical |

## Archive

| Document | Role | Guardian | WP links | Status |
|---|---|---|---|---|
| `docs/archive/README.md` | Archive index. | `PM_ORCHESTRATOR` | none | archived/supporting |

## Stale / Duplicated Risk List

- `docs/VERSION_MAP.md` and `docs/ROADMAP.md` still contain older `v0.7-prep` style labels; use `VERSION_ROADMAP.md` for WP-012..WP-018 sequencing.
- `docs/CURRENT_MILESTONE.md` remains useful stage evidence but its headline version label is older than the WP-011B/011C Project OS state.
- `docs/project_management/CS2_AI_COACH_MASTER_CURATION_PLAYBOOK.md` and `CS2_AI_COACH_PROJECT_CURATION_HANDOFF.md` are valuable historical operating manuals but predate WP-011B/011C.
- Older strategy/scoring/prompt docs are supporting or historical, not current instructions.
- `docs/audit/FULL_PROJECT_AUDIT_*` reports are point-in-time evidence and should not override Hot context.
- `docs/audit/WP_018_DOCUMENTATION_GOVERNANCE_AUDIT_REPORT.md` is an out-of-band governance audit evidence file. It does not consume the planned `WP-018` product ID.
