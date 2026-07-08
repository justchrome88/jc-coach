# LEAN-DOCS-01 Apply Lean Root Contract Report

Task ID: `LEAN-DOCS-01_APPLY_LEAN_ROOT_CONTRACT`
Date: 2026-07-09
Mode: `docs-only / root-contract-apply / file-backed`

## 1. Result

`PASS_WITH_WARNINGS`

The root `AGENTS.md` was replaced with a lean Codex Native root contract while
preserving the task-required universal safety rules and current JC Coach product
guardrails.

Warning: preflight found the required triage input file
`docs/refactor/LEAN_ROOT_CONTRACT_TRIAGE.md` as an existing untracked file.
Because it is the named input artifact for this task and no other dirty main
repo files were present, it was treated as explained task context. It remains
untracked.

## 2. Changed Files

- `AGENTS.md`
- `docs/refactor/LEAN-DOCS-01_APPLY_LEAN_ROOT_CONTRACT_REPORT.md`

## 3. What Was Removed From `AGENTS.md`

- Mandatory `docs/audit/WP_*` report rule for every WP.
- Discovery-result YAML template.
- PM decomposition and follow-up machinery.
- Detailed DB SHA evidence matrix.
- Detailed schema-changing and startup compatibility policy.
- FH-030/FH-031/FH-032 historical schema notes.
- Detailed old roadmap list.
- Foundation recovery history as active operating policy.
- Wording that made ordinary tasks inherit Foundation-era workflow
  bureaucracy.

## 4. What Safety Rules Were Preserved

- JC Coach remains the primary product.
- The current explicit user task can be stricter than `AGENTS.md`.
- Do not read all docs by default.
- Hot context remains `AGENTS.md`, `docs/CURRENT_STATUS.md`,
  `docs/HANDOFF.md` and `docs/project_management/WP_REGISTRY.md`.
- Warm docs are read only when task-relevant.
- Old reports, prompts and audits are evidence/history only.
- No DB/schema/data/import/parser/evaluator/service/deploy/package/raw-demo
  mutation without explicit scope.
- Never commit DBs, backups, uploads, demos, `.dem`, `.dem.bz2` or
  `__pycache__`.
- Show `git status --short` before work.
- No `git add`, commit or push unless explicitly authorized.
- `STEAM_IMPORT_MAX_DEMOS_PER_RUN` remains `1` unless an explicit cap-change
  task changes it.
- Playlist/mode remains unknown or provenance-only unless reliable metadata
  exists.
- Weak metrics stay caveated.
- Recommendation `#5` remains the current accepted active hard recommendation
  unless a future accepted task changes it.
- WP-018 and major CS2 product work remain paused unless explicitly authorized
  by the current user task and Hot docs.
- Public/friends readiness remains blocked.
- Stop as `BLOCKED` on dirty worktree, missing authorization,
  source-of-truth conflict or unsafe side effect.

## 5. Checks Run

- `wc -l AGENTS.md` -> `138 AGENTS.md`.
- `git diff --check` -> passed.
- `git status --short` -> `M AGENTS.md`, `?? docs/refactor/`.

## 6. Remaining Drift / Warnings

- Product Hot docs still carry the post-foundation lane as
  `POST_FOUNDATION_AUDIT_AND_STABILIZATION`, while PM-side memory from
  `LEAN-DOCS-00` reports newer post-foundation repair closure state and higher
  readiness. This task intentionally did not reconcile that drift.
- The existing triage artifact `docs/refactor/LEAN_ROOT_CONTRACT_TRIAGE.md`
  remains untracked in the main repository.
- No `foundation/core/*` or `foundation/adapters/codex/*` files were created;
  detailed operating mechanics remain in existing Warm docs until a separate
  task scopes further extraction.

## 7. Exact Next Recommended Task

`LEAN-DOCS-02_RECONCILE_HOT_PM_PRODUCT_DRIFT`

Goal: reconcile the known drift between product Hot docs and PM Hot docs
without broad cleanup, then decide whether any focused Foundation/core or
Codex-adapter extraction is still needed.
