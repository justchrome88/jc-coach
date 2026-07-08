# LEAN-DOCS-03 Active Context Inventory And Archive Plan

Task ID: `LEAN-DOCS-03_ACTIVE_CONTEXT_INVENTORY_AND_ARCHIVE_PLAN`

Date: 2026-07-09

Role: Codex Documentation Steward

Mode: docs-only / inventory-only / file-backed

## 1. Result

`PASS_WITH_WARNINGS`

The active context inventory and archive plan were created. No files were
moved, deleted, archived, committed, pushed, or changed outside the scoped
report and CSV inventory.

Warning: the inventory is intentionally path-based and grouped from tracked file
lists, not a full content audit of every historical document.

## 2. Branch / Head

- Branch: `cona`
- HEAD: `c0f2977c1ea73f19e9e3357a97a4f321e23ca53d`

## 3. Changed Files

- `docs/refactor/LEAN-DOCS-03_ACTIVE_CONTEXT_INVENTORY_AND_ARCHIVE_PLAN.md`
- `exports/lean_docs_inventory.csv`

## 4. Inputs Used

Hot docs read:

- `AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/project_management/WP_REGISTRY.md`

File lists used:

- `/tmp/jc-coach-files.txt` from `/opt/jc-coach` (`393` tracked files)
- `/tmp/jc-coach-pm-files.txt` from `/opt/jc-coach-pm` (`342` tracked files)

No PM repo files were modified.

## 5. Current Hot Docs

Keep these as ordinary-task Hot context:

- `AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/project_management/WP_REGISTRY.md`

Rationale: these are the explicit root contract, current state, compact
new-session bootstrap, and canonical WP registry.

## 6. Warm Product Docs

Keep as task-relevant Warm product context, not ordinary-task Hot context:

- `docs/ARCHITECTURE.md`
- `docs/API_CONTRACTS.md`
- `docs/METRICS.md`
- `docs/CS2_DOMAIN_CONTRACT.md`
- `docs/RECOMMENDATIONS.md`
- `docs/AI_COACH.md`
- `docs/AI_COACH_PROVIDER_ARCHITECTURE.md`
- `docs/STEAM_IMPORT.md`
- `docs/STEAM_IMPORT_ARCHITECTURE.md`
- `docs/BACKUP_RESTORE.md`
- `docs/DEPLOYMENT.md`
- `docs/MIGRATIONS.md`
- `docs/SECURITY.md`
- `docs/TESTING.md`
- `docs/KNOWN_LIMITATIONS.md`

Rationale: these docs describe product, runtime, domain, metric, import,
deployment, security, migration, test, and limitation behavior. They should be
read only when the active task touches that area.

## 7. Warm Process Docs

Keep as task-relevant Warm process/governance context:

- `docs/project_management/PROJECT_OPERATING_PROTOCOL.md`
- `docs/project_management/AGENT_WORKFLOW.md`
- `docs/project_management/MASTER_WP_CHECKLIST.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/project_management/VERSION_ROADMAP.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/DOCS_INDEX.md`
- `docs/project_management/DOCS_MAP.md`
- `docs/agents/roles/*`
- `docs/agents/*.md`

Rationale: these are useful for governance, planning, role invocation, WP
workflow, acceptance, roadmap, or docs-routing tasks, but should not be loaded
by default for ordinary implementation tasks.

## 8. Cold / History Groups

Cold/history groups identified from paths:

- `docs/audit/WP_011*` through most completed `WP_017*` reports: accepted
  evidence/history, read only when a task needs the specific WP evidence.
- `docs/audit/WP_018_DOCUMENTATION_GOVERNANCE_AUDIT_REPORT.md`: out-of-band
  governance evidence, not planned `WP-018` product work.
- `docs/audit/WP_018A_COACH_OUTPUT_QUALITY_DIAGNOSIS_REPORT.md`: preserved
  product restart context, read only for an authorized WP-018 restart path.
- `docs/audits/2026-07-06-agentic-readiness-audit/*`: historical
  readiness-audit evidence.
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/*`:
  foundation and post-foundation task evidence.
- `docs/tasks/*`: old task prompts/TZ material.
- `instructions/*`: old prompts/specs/sample instruction material.
- `/opt/jc-coach-pm/archive/*`, `reviews/*`, `summaries/tasks/*`,
  `runtime_snapshots/*`: PM memory/history, not active product context.

## 9. Archive Batch 1 Proposal

Aggressive but safe Archive Batch 1 groups:

- Completed task cards:
  `/opt/jc-coach-pm/archive/completed_outbox/*` and
  `/opt/jc-coach-pm/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_cards/*`
- Superseded task cards:
  `/opt/jc-coach-pm/archive/superseded_task_cards/*` and
  `/opt/jc-coach-pm/archive/superseded_outbox/*`
- Blocked/completed outbox material:
  `/opt/jc-coach-pm/archive/blocked_outbox/*`,
  `/opt/jc-coach-pm/archive/blocked_reports/*`, and empty outbox placeholders
  where applicable.
- Old Foundation Hardening reports:
  `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-*`
- Old post-foundation repair/review reports after their result is summarized in
  current state:
  `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/POST-FOUNDATION-*`
- Old stabilization/Foundation process reports:
  `docs/audit/STAGE_*`, `docs/audit/FULL_PROJECT_*`,
  `docs/audit/INSTRUCTIONS_*`, `docs/audit/DOCUMENT_*`
- Old prompts and task/TZ material:
  `docs/tasks/*`, `instructions/*`,
  `/opt/jc-coach-pm/prompts/*`, and
  `/opt/jc-coach-pm/archive/accepted_plans/*/prompts/*`
- Runtime snapshots:
  `/opt/jc-coach-pm/runtime_snapshots/*`
- Duplicate summaries:
  `/opt/jc-coach-pm/summaries/tasks/*`
- Stale checkpoint/review docs:
  `/opt/jc-coach-pm/reviews/*CHECKPOINT*`,
  `/opt/jc-coach-pm/reviews/*recovery*`, and old FH review batches.
- Old PM reviews:
  `/opt/jc-coach-pm/reviews/2026-07-06_*`,
  `/opt/jc-coach-pm/reviews/2026-07-07_*`,
  `/opt/jc-coach-pm/reviews/2026-07-08_FH-*`

Recommended archive mechanics for `LEAN-DOCS-04_ARCHIVE_HISTORICAL_PROCESS_MASS`:

- Move only files matched by reviewed Batch 1 groups.
- Preserve path provenance in archive destination naming.
- Do not rewrite Hot docs unless a broken link must be repaired.
- Produce a before/after file-count summary and `git diff --check`.

## 10. Do-Not-Touch Groups

Do not include these in Archive Batch 1:

- `AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/project_management/WP_REGISTRY.md`
- `docs/ARCHITECTURE.md`
- `docs/METRICS.md`
- `docs/CS2_DOMAIN_CONTRACT.md`
- `docs/RECOMMENDATIONS.md`
- `docs/AI_COACH.md`
- `docs/STEAM_IMPORT.md`
- Source code: `app/*`
- Tests and fixtures: `tests/*`
- Scripts and tooling used by gates/runtime: `scripts/*`, `tools/*`
- DB/data/uploads/raw demo/storage placeholders and any untracked data:
  `data/*`
- Service/deploy/runtime config: `deploy/*`, `Dockerfile`,
  `docker-compose.yml`
- Package/dependency config: `pyproject.toml`,
  `tools/steam-gc/package.json`, `tools/steam-gc/package-lock.json`
- PM repo current memory/control files unless a PM-memory-specific task scopes
  them: `PM_STATE.md`, `ACTIVE_PLAN.md`, `memory/*`, `indexes/*`,
  `docs/pm_memory/*`, `config/model_policy.json`, `tools/*`

## 11. Unknown / Review Groups

Review manually before archiving, because path names alone are not enough:

- `AGENT.md`
- `LATER.md`
- `WORKLOG.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/PROJECT_CONTROL.md`
- `docs/PROJECT_GOVERNANCE.md`
- `docs/PROJECT_OS.md`
- `docs/ROADMAP.md`
- `docs/VERSION_MAP.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/PUBLIC_DEPLOYMENT_CHECKLIST.md`
- `docs/PRODUCT_EXECUTION_STRATEGY.md`
- `docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md`
- `docs/NON_STOP_DEVELOPMENT_PROMPTS.md`
- `docs/feature_roadmap_scoring_ru.xlsx`
- `docs/metrics_roadmap_scoring_ru.xlsx`
- `/opt/jc-coach-pm` root docs not already marked as current memory or archive
  candidates.
- `/opt/jc-coach-pm/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/*.md`
  top-level tracker/ledger/plan files.

## 12. Risks

- Path-based classification can misclassify a file whose title is stale but
  content is still authoritative.
- Historical reports may be linked from current docs; the archive task should
  check links before and after moves.
- `docs/foundation_hardening/.../RISK_REGISTER.md` is current source-of-truth
  evidence and should not be swept into a broad folder move.
- PM repo files may contain useful recovery memory; archive in product repo
  should not assume PM repo cleanup is authorized.
- Any future archive task must still obey DB/import/parser/evaluator/service
  safety rules and avoid touching product code, tests, data, runtime config, or
  dependency files.

## 13. Exact Next Recommended Task

`LEAN-DOCS-04_ARCHIVE_HISTORICAL_PROCESS_MASS`

Scope recommendation: archive only the reviewed Batch 1 historical process
groups above, with no product/runtime/DB/import/parser/evaluator/service
changes.
