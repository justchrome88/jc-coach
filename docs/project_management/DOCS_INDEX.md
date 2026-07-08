# Documentation Index

Last updated: 2026-07-08.

Human-readable navigation map. This file does not replace `AGENTS.md`,
`docs/CURRENT_STATUS.md`, `docs/project_management/WP_REGISTRY.md` or
`docs/project_management/DOCS_MAP.md`; it helps people find the right document
without moving or renaming files.

> Status: Navigation document.
> Do not use this file as current project state.
> Current source of truth: `AGENTS.md`, `docs/CURRENT_STATUS.md`,
> `docs/project_management/WP_REGISTRY.md`.

## Hot / Warm / Cold Context

Per-task Hot context:

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/project_management/WP_REGISTRY.md`

New-session Hot context additionally includes:

4. `docs/HANDOFF.md`

Warm context is read only when the task requires that domain: roadmap/planning,
acceptance/promotion, deploy/service, testing/gates, DB/data integrity,
import/parser/evaluator, recommendations, UI/web routes, security or historical
WP review. Before reading Warm docs, Codex should state which files are needed
and why.

`docs/project_management/PROJECT_OPERATING_PROTOCOL.md` and
`docs/project_management/MASTER_WP_CHECKLIST.md` are Warm governance/planning
references. `docs/project_management/AGENT_WORKFLOW.md` is a Warm governance
role workflow, task type routing, invocation modes, output modes and prompt
contract reference, including the control-plane protection policy.
`docs/agents/roles/*` are Warm role definitions. These files are not per-task
Hot context.

Cold context includes old audit reports, stage reports, old prompts, archived
historical task prompts, archived historical instruction artifacts, old
roadmap/version docs and generated data reports. Cold files are
evidence/history and must not override Hot context.

## Project OS / Control

- `AGENTS.md` - only root Codex operating contract.
- `AGENT.md` - superseded pointer; do not use as active contract.
- `docs/README.md` - human documentation entrypoint.
- `docs/PROJECT_OS.md` - historical/superseded operational entrypoint; do not use for current state.
- `docs/HANDOFF.md` - current state, next WP and do-not-do list.
- `docs/PROJECT_CONTROL.md` - supporting governance/product control reference; current operating hierarchy starts with `AGENTS.md` and Hot context.
- `docs/PROJECT_GOVERNANCE.md` - governance, WP gates, evidence policy.
- `docs/CURRENT_STATUS.md` - current product state.
- `docs/CURRENT_MILESTONE.md` - historical/superseded milestone evidence; not current roadmap or product-state truth.
- `docs/project_management/PROJECT_OPERATING_PROTOCOL.md` - Warm governance protocol for roles, WP lifecycle, blockers, reports and commit flow.
- `docs/project_management/AGENT_WORKFLOW.md` - Warm repo-native WP role workflow, control-plane protection policy, invocation modes, output modes, task type profiles, Task Card prompt contract and Documentation Steward / Docs Currency Agent checks; not per-task Hot context.

## Project Management

- `docs/project_management/VERSION_ROADMAP.md` - version-to-WP roadmap from `v0.4.2` to `v1.0`.
- `docs/project_management/WORK_PACKAGE_BACKLOG.md` - WP objectives, guardians, forbidden actions, evidence and exits.
- `docs/project_management/ACCEPTANCE_MATRIX.md` - feature acceptance by version and guardian.
- `docs/project_management/DOCS_MAP.md` - documentation ownership, source-of-truth and stale-risk map.
- `docs/project_management/DOCS_INDEX.md` - this human navigation index.
- `docs/project_management/MASTER_WP_CHECKLIST.md` - Warm/Cold human-readable full WP campaign map; registry remains canonical for status/dependencies/report paths.
- `docs/project_management/AGENT_WORKFLOW.md` - Warm governance/process doc for PM, Implementation, QA and Documentation Steward roles, control-plane protection policy, invocation modes, output modes, task type profiles and standard prompt/report contracts inside WP lifecycle.
- `docs/ROADMAP.md` - historical/archive-candidate roadmap overview; do not use as current roadmap truth.
- `docs/VERSION_MAP.md` - historical/archive-candidate version status map; do not use as current version truth.
- `docs/RELEASE_CHECKLIST.md` - release/friends/public gate checklist.
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/` - current
  foundation hardening recovery plan after the 2026-07-06 agentic-readiness
  audit; governs restricted scope until its readiness gate passes.
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/06_ROADMAP_PAUSE_AND_RESUME.md` - roadmap pause/resume control note for the restricted
  foundation hardening lane and WP-018 resume path.

## Agent Workflow And Guardians

- `docs/agents/README.md` - Warm index for workflow role cards and domain guardian docs.
- `docs/agents/roles/PM_ORCHESTRATOR.md` - Warm workflow role card for task routing, scope, Warm docs selection, stop conditions and handoffs.
- `docs/agents/roles/IMPLEMENTATION_AGENT.md` - Warm workflow role card for scoped edits and implementation handoff.
- `docs/agents/roles/QA_REVIEWER.md` - Warm workflow role card for review, checks, risk assessment and verdicts.
- `docs/agents/roles/DOCUMENTATION_STEWARD.md` - Warm workflow role card for docs currency, required doc updates and closure readiness.
- `docs/agents/roles/ROLE_CARD_TEMPLATE.md` - Warm template for future approved role cards.
- `docs/agents/PM_ORCHESTRATOR.md` - supporting legacy/domain PM guardrail for WP scope, handoff, version map and evidence gates; canonical workflow PM role card is `docs/agents/roles/PM_ORCHESTRATOR.md`.
- `docs/agents/DB_GUARDIAN.md` - production DB, migrations and contamination safety.
- `docs/agents/RUNTIME_GUARDIAN.md` - FastAPI/Jinja runtime, service freshness and smoke checks.
- `docs/agents/TEST_GUARDIAN.md` - test isolation and safe verification.
- `docs/agents/IMPORT_GUARDIAN.md` - Steam/import/demo parser boundaries.
- `docs/agents/METRICS_GUARDIAN.md` - Metric Truth, recommendation evidence and AI output truth.
- `docs/agents/UI_COACH_GUARDIAN.md` - `/coach` UI honesty and read-only rendering.

## Product Architecture

- `docs/ARCHITECTURE.md` - system shape and boundaries.
- `docs/CS2_DOMAIN_CONTRACT.md` - CS2 match/round domain boundaries,
  glossary, source limits, unavailable model rules and map-registry plan.
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
- `docs/STEAM_MATCH_DATES_RU.md` - supporting Steam/import date policy; not current source-of-truth.
- `docs/DEMO_DEEP_PARSER_TZ_RU.md` - historical/supporting parser context/spec; not current source-of-truth.
- `docs/DEMO_STORAGE_TZ.md` - historical/supporting demo storage lifecycle plan; not current source-of-truth.

## Metrics / Recommendations / AI

- `docs/METRICS.md` - canonical Metric Truth contract.
- `docs/RECOMMENDATIONS.md` - recommendation loop and planner rules.
- `docs/AI_COACH.md` - AI provider/output truth.
- `docs/METRICS_ROADMAP_SCORING_RU.md` - metric scoring/wishlist, historical/supporting; not current source-of-truth.
- `docs/AI_COACH_PROVIDER_ARCHITECTURE.md` - older AI provider memo, supporting/historical.
- `docs/AI_RECOMMENDATIONS_AIM_EXECUTION_PLAN_RU.md` - older AI/recommendation plan, historical/completed; not current source-of-truth.

## Testing / Security

- `docs/TESTING.md` - safe test commands and isolation rules.
- `docs/SECURITY.md` - auth/security current truth and friends/public blockers.
- `docs/audit/API_SECURITY_INVENTORY.md` - security inventory evidence.
- `docs/audit/STAGE_1_SECURITY_P0_REVIEW.md` - Security P0 review evidence.
- `docs/audit/STAGE_2_OWNERSHIP_REVIEW.md` - ownership review evidence.

## Audit Evidence

- `docs/audits/2026-07-06-agentic-readiness-audit/` - read-only
  agentic-readiness audit evidence and matrix; produced the `66%` readiness
  recovery lane.
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

- `docs/archive/lean-docs-2026-07-09/from-root/docs/tasks/STABILIZATION_STAGE_0_TZ_CS2_AI_COACH.md` through `docs/archive/lean-docs-2026-07-09/from-root/docs/tasks/STABILIZATION_STAGE_9_COACH_FIRST_UI_TZ_CS2_AI_COACH.md` - archived historical stage task specs; not active workflow.
- `docs/archive/lean-docs-2026-07-09/from-root/docs/tasks/FULL_PROJECT_AUDIT_AFTER_DOCS_TASK.md` - archived historical earlier audit task.
- `docs/archive/lean-docs-2026-07-09/from-root/docs/tasks/INSTRUCTIONS_CONSOLIDATION_TASK.md` - archived historical earlier docs consolidation task.
- `docs/archive/lean-docs-2026-07-09/from-root/instructions/*` - archived historical original prompts/specs; not active workflow or current source of truth.

## Historical / Supporting

- `docs/project_management/CS2_AI_COACH_MASTER_CURATION_PLAYBOOK.md` - historical/archive-candidate operating playbook; superseded by `AGENTS.md`, `AGENT_WORKFLOW.md` and current Hot context.
- `docs/project_management/CS2_AI_COACH_PROJECT_CURATION_HANDOFF.md` - historical/archive-candidate handoff manual; superseded by `docs/HANDOFF.md`.
- `docs/PRODUCT_EXECUTION_STRATEGY.md` - older strategy memo, historical/superseded; not current source-of-truth.
- `docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md` - older implementation plan, historical/superseded; not current source-of-truth.
- `docs/NON_STOP_DEVELOPMENT_PROMPTS.md` - historical/archive-candidate prompt library; not active workflow.
- `docs/COMPETITOR_FEATURE_MATRIX.md` - market comparison, supporting.
- `docs/FEATURE_ROADMAP_SCORING.md` - feature scoring, historical/supporting; not current roadmap truth.
- `docs/feature_roadmap_scoring_ru.xlsx` - supporting spreadsheet artifact.
- `docs/metrics_roadmap_scoring_ru.xlsx` - supporting spreadsheet artifact.
- `docs/archive/README.md` - archive index.

## Current Active WP

See `docs/CURRENT_STATUS.md` and `docs/project_management/WP_REGISTRY.md`.
Do not use this navigation index as current WP truth.
