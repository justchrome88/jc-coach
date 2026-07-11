# LEAN-DOCS-02 Single Workspace And Hot Drift Fix Report

Task ID: `LEAN-DOCS-02_SINGLE_WORKSPACE_AND_HOT_DRIFT_FIX`
Date: 2026-07-09
Mode: `docs-only / focused cleanup / file-backed`

## Result

`PASS_WITH_WARNINGS`

Product Hot docs now record the single-workspace Codex convention and the
current lean docs cleanup / Codex Native simplification mini-phase without
changing product readiness, WP registry state, code, data or PM memory files.

## Changed Files

- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/refactor/LEAN-DOCS-02_SINGLE_WORKSPACE_AND_HOT_DRIFT_FIX_REPORT.md`

## What Drift Was Fixed

- Future Codex work should start from `/opt/jc-coach`.
- Codex PM, Executor, Reviewer and Documentation Steward are prompt roles, not
  mandatory separate Codex windows.
- `/opt/jc-coach-pm` is PM memory, archive or reference only when explicitly
  needed, not the primary launch workspace.
- The current organizational mini-phase is `LEAN_DOCS_CLEANUP` /
  `CODEX_NATIVE_SIMPLIFICATION`.
- JC Coach remains the product; JC Forge is not being built now.
- WP-018 and major CS2 product work remain paused unless explicitly restarted.
- Public/friends readiness remains blocked.

## What Was Intentionally Not Touched

- `AGENTS.md`
- `docs/project_management/WP_REGISTRY.md`
- Code and tests
- DB, schema, data files, imports, parser, evaluator, services and deploy
  configuration
- Raw demos, uploads and backups
- PM repo files under `/opt/jc-coach-pm`
- Broad documentation cleanup, archiving, deletion or file moves

## Checks

- Preflight `git status --short` -> clean
- Preflight branch -> `cona`
- Preflight HEAD -> `1c3633e3ec7c581eafb56ed23090aa49ff7acb02`
- `git diff --check` -> passed
- `git status --short` ->
  - `M docs/CURRENT_STATUS.md`
  - `M docs/HANDOFF.md`
  - `?? docs/refactor/LEAN-DOCS-02_SINGLE_WORKSPACE_AND_HOT_DRIFT_FIX_REPORT.md`

## Risks / Warnings

- Product Hot docs still preserve the prior foundation/post-foundation
  readiness language. This task only added the active organizational
  mini-phase and single-workspace continuation rule.
- PM memory still contains older dual-Codex wording and later post-foundation
  closure details. PM repo edits were explicitly out of scope.
- No product restart, WP-018 restart, JC Forge work, public/friends unlock,
  package work, data mutation or runtime change was performed.

## Recommended Next Task

Return to JC Coach product work after lean docs cleanup, or run one narrow
PM-memory cleanup task that updates `/opt/jc-coach-pm` wording to match the
single-workspace prompt-role model without changing product source of truth.
