# Documentation Index

Last updated: 2026-07-04.

Human-readable navigation map. This file does not replace `docs/PROJECT_CONTROL.md` or `docs/project_management/DOCS_MAP.md`; it helps people find the right document without moving or renaming files.

## Project OS / Control

- `AGENT.md` - rules for Codex agents.
- `docs/README.md` - human documentation entrypoint.
- `docs/PROJECT_OS.md` - shortest operational entrypoint.
- `docs/HANDOFF.md` - current state, next WP and do-not-do list.
- `docs/PROJECT_CONTROL.md` - top source of truth.
- `docs/PROJECT_GOVERNANCE.md` - governance, WP gates, evidence policy.
- `docs/CURRENT_STATUS.md` - current product state.
- `docs/CURRENT_MILESTONE.md` - current/historical hardening milestone detail.

## Project Management

- `docs/project_management/VERSION_ROADMAP.md` - version-to-WP roadmap from `v0.4.2` to `v1.0`.
- `docs/project_management/WORK_PACKAGE_BACKLOG.md` - WP objectives, guardians, forbidden actions, evidence and exits.
- `docs/project_management/ACCEPTANCE_MATRIX.md` - feature acceptance by version and guardian.
- `docs/project_management/DOCS_MAP.md` - documentation ownership, source-of-truth and stale-risk map.
- `docs/project_management/DOCS_INDEX.md` - this human navigation index.
- `docs/ROADMAP.md` - older roadmap overview; use with `VERSION_ROADMAP.md`.
- `docs/VERSION_MAP.md` - older version status map; contains stale-label risk.
- `docs/RELEASE_CHECKLIST.md` - release/friends/public gate checklist.

## Guardians

- `docs/agents/PM_ORCHESTRATOR.md` - WP scope, handoff, version map and evidence gates.
- `docs/agents/DB_GUARDIAN.md` - production DB, migrations and contamination safety.
- `docs/agents/RUNTIME_GUARDIAN.md` - FastAPI/Jinja runtime, service freshness and smoke checks.
- `docs/agents/TEST_GUARDIAN.md` - test isolation and safe verification.
- `docs/agents/IMPORT_GUARDIAN.md` - Steam/import/demo parser boundaries.
- `docs/agents/METRICS_GUARDIAN.md` - Metric Truth, recommendation evidence and AI output truth.
- `docs/agents/UI_COACH_GUARDIAN.md` - `/coach` UI honesty and read-only rendering.

## Product Architecture

- `docs/ARCHITECTURE.md` - system shape and boundaries.
- `docs/FEATURES_RU.md` - implemented features summary, supporting.
- `docs/DECISIONS.md` - current decisions.
- `docs/KNOWN_LIMITATIONS.md` - known non-readiness areas.

## Runtime / Operations

- `docs/DEPLOYMENT.md` - deployment shape and runtime notes.
- `docs/BACKUP_RESTORE.md` - backup and restore runbook.
- `docs/MIGRATIONS.md` - migration discipline and copy-check policy.
- `docs/PUBLIC_DEPLOYMENT_CHECKLIST.md` - public deployment gate, currently blocked by security.
- `docs/CHANGELOG.md` - curated change history.

## Import / Steam / Parser

- `docs/STEAM_IMPORT.md` - canonical Steam import truth.
- `docs/STEAM_IMPORT_ARCHITECTURE.md` - deeper Steam architecture, supporting.
- `docs/STEAM_MATCH_DATES_RU.md` - Steam match date policy.
- `docs/DEMO_DEEP_PARSER_TZ_RU.md` - parser context/spec, supporting.
- `docs/DEMO_STORAGE_TZ.md` - demo storage lifecycle plan.

## Metrics / Recommendations / AI

- `docs/METRICS.md` - canonical Metric Truth contract.
- `docs/RECOMMENDATIONS.md` - recommendation loop and planner rules.
- `docs/AI_COACH.md` - AI provider/output truth.
- `docs/METRICS_ROADMAP_SCORING_RU.md` - metric scoring/wishlist, historical/supporting.
- `docs/AI_COACH_PROVIDER_ARCHITECTURE.md` - older AI provider memo, supporting/historical.
- `docs/AI_RECOMMENDATIONS_AIM_EXECUTION_PLAN_RU.md` - older AI/recommendation plan, historical.

## Testing / Security

- `docs/TESTING.md` - safe test commands and isolation rules.
- `docs/SECURITY.md` - auth/security current truth and friends/public blockers.
- `docs/audit/API_SECURITY_INVENTORY.md` - security inventory evidence.
- `docs/audit/STAGE_1_SECURITY_P0_REVIEW.md` - Security P0 review evidence.
- `docs/audit/STAGE_2_OWNERSHIP_REVIEW.md` - ownership review evidence.

## Audit Evidence

- `docs/audit/WP_011B_PROJECT_OS_IMPLEMENTATION_REPORT.md` - Project OS implementation evidence.
- `docs/audit/WP_011C_ROADMAP_DOCS_WIRING_REPORT.md` - roadmap/docs wiring evidence.
- `docs/audit/WP_011D_DOCUMENTATION_NAVIGATION_INDEX_REPORT.md` - documentation navigation index evidence.
- `docs/audit/BUGFIX_001_COACH_RUNTIME_FAILURE_DIAGNOSIS.md` - runtime stale-process incident diagnosis.
- `docs/audit/STAGE_1_*` through `docs/audit/STAGE_9_*` - stage implementation/review evidence.
- `docs/audit/*_INVENTORY.md` - domain inventories.
- `docs/audit/DOCUMENT_CONFLICTS.md` - docs conflict inventory.
- `docs/audit/DOCUMENT_DEPRECATION_PLAN.md` - historical doc handling policy.
- `docs/audit/FULL_PROJECT_AUDIT_*` - point-in-time project audits, supporting.

## Task Specs

- `docs/tasks/STABILIZATION_STAGE_0_TZ_CS2_AI_COACH.md` through `docs/tasks/STABILIZATION_STAGE_9_COACH_FIRST_UI_TZ_CS2_AI_COACH.md` - historical stage task specs.
- `docs/tasks/FULL_PROJECT_AUDIT_AFTER_DOCS_TASK.md` - earlier audit task.
- `docs/tasks/INSTRUCTIONS_CONSOLIDATION_TASK.md` - earlier docs consolidation task.

## Historical / Supporting

- `docs/project_management/CS2_AI_COACH_MASTER_CURATION_PLAYBOOK.md` - older operating playbook; predates WP-011B/011C.
- `docs/project_management/CS2_AI_COACH_PROJECT_CURATION_HANDOFF.md` - older handoff manual; predates WP-011B/011C.
- `docs/PRODUCT_EXECUTION_STRATEGY.md` - older strategy, historical.
- `docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md` - older implementation plan, historical.
- `docs/NON_STOP_DEVELOPMENT_PROMPTS.md` - prompt library, historical unless reactivated.
- `docs/COMPETITOR_FEATURE_MATRIX.md` - market comparison, supporting.
- `docs/FEATURE_ROADMAP_SCORING.md` - feature scoring, supporting/historical.
- `docs/feature_roadmap_scoring_ru.xlsx` - supporting spreadsheet artifact.
- `docs/metrics_roadmap_scoring_ru.xlsx` - supporting spreadsheet artifact.
- `docs/archive/README.md` - archive index.

## Current Active WP

```text
WP-012 DB Contamination Guardrails
Target version: v0.4.2
```

See `docs/project_management/WORK_PACKAGE_BACKLOG.md` for scope and `docs/project_management/ACCEPTANCE_MATRIX.md` for acceptance criteria.

