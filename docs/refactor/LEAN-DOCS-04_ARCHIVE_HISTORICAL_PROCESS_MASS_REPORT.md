# LEAN-DOCS-04 Archive Historical Process Mass Report

Task ID: `LEAN-DOCS-04_ARCHIVE_HISTORICAL_PROCESS_MASS`

Date: 2026-07-09

Role: Codex Documentation Steward

Mode: docs-only / archive-move-only / file-backed

## Result

`PASS_WITH_WARNINGS`

Archived explicitly scoped historical process documentation from the product
repo without deleting files and without changing product behavior, DB/data,
runtime, tests, code, tools, dependencies or `/opt/jc-coach-pm`.

Warning: optional link check found remaining Warm process-doc references to
old `docs/tasks/*` and `instructions/*` paths. They were not edited in this
archive-move task because the task restricted reads to Hot docs, the prior
inventory and the CSV. One direct Hot-doc link to the moved FH-125_128 report
was updated in `docs/CURRENT_STATUS.md`.

## Preflight

- `git status --short`: clean before work.
- Branch: `cona`.
- HEAD: `a0bf68bde617f93b66478b0597bd50a2eb198d41`.

## Inputs Read

- `AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/project_management/WP_REGISTRY.md`
- `docs/refactor/LEAN-DOCS-03_ACTIVE_CONTEXT_INVENTORY_AND_ARCHIVE_PLAN.md`
- `exports/lean_docs_inventory.csv`

## Archive Destination

- Archive root: `docs/archive/lean-docs-2026-07-09/`
- Preserved-path root: `docs/archive/lean-docs-2026-07-09/from-root/`
- Manifest: `docs/archive/lean-docs-2026-07-09/ARCHIVE_MANIFEST.md`

## Moved File Count

`101`

## Moved Groups

- `docs/audit/STAGE_*`: `17` files.
- `docs/audit/FULL_PROJECT_*`: `3` files.
- `docs/audit/INSTRUCTIONS_*`: `3` files.
- `docs/audit/DOCUMENT_*`: `2` files.
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-*`: `43` files.
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/POST-FOUNDATION-*`: `7` files.
- `docs/tasks/*`: `12` files.
- `instructions/*`: `14` files.

## Changed Files Summary

- Created archive manifest:
  `docs/archive/lean-docs-2026-07-09/ARCHIVE_MANIFEST.md`.
- Created task report:
  `docs/refactor/LEAN-DOCS-04_ARCHIVE_HISTORICAL_PROCESS_MASS_REPORT.md`.
- Moved `101` tracked historical process files with `git mv` into
  `docs/archive/lean-docs-2026-07-09/from-root/`.
- Updated one direct Hot-doc link in `docs/CURRENT_STATUS.md` to the archived
  FH-125_128 report path.

## Skipped / Manual-Review Groups

These were not moved:

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

## Do-Not-Touch Groups Preserved

- `AGENTS.md`
- `docs/HANDOFF.md`
- `docs/project_management/WP_REGISTRY.md`
- Protected product docs such as `docs/ARCHITECTURE.md`, `docs/METRICS.md`,
  `docs/CS2_DOMAIN_CONTRACT.md`, `docs/RECOMMENDATIONS.md`,
  `docs/AI_COACH.md`, `docs/STEAM_IMPORT.md` and
  `docs/KNOWN_LIMITATIONS.md`.
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/RISK_REGISTER.md`
- `app/*`
- `tests/*`
- `scripts/*`
- `tools/*`
- `data/*`
- `deploy/*`
- `Dockerfile`
- `docker-compose.yml`
- `pyproject.toml`
- `tools/steam-gc/package.json`
- `tools/steam-gc/package-lock.json`
- `/opt/jc-coach-pm`

## Safety Notes

- No files were deleted.
- No commits or pushes were performed.
- No import/parser/evaluator/manual evaluator jobs were run.
- No live Steam/Valve import was run.
- No service/deploy restart or runtime config change was performed.
- No package/dependency files were changed.
- Product status was not changed.

## Checks

- `git diff --check`: `PASS` with no output.
- `git diff --cached --check`: `PASS` with no output.
- New-file whitespace checks for the archive manifest and this report:
  `PASS` with no output.
- Optional Hot/project-management link grep: `PASS_WITH_WARNINGS`.
  - Direct Hot-doc FH-125_128 report path was updated to archived location.
  - Warm process-doc references to archived `docs/tasks/*` and
    `instructions/*` remain for a separately scoped link cleanup.

## Recommended Next Task

`LEAN-DOCS-05_ARCHIVE_LINK_POINTER_CLEANUP`: update Warm process-doc pointers
that still mention archived `docs/tasks/*` and `instructions/*` paths, using a
read scope that explicitly includes the affected Warm docs.
