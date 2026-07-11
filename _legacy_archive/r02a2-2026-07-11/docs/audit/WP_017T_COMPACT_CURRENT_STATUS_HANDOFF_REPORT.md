# WP-017T Compact Current Status and Handoff Report

## 1. Summary

WP-017T compressed the active current-state layer so future ChatGPT/Codex prompts can stay short while current project truth remains in the repository. `docs/CURRENT_STATUS.md` now holds a compact product/runtime/blocker snapshot, `docs/HANDOFF.md` now serves as a new-session bootstrap, `docs/DECISIONS.md` records the current governance decisions, and `docs/project_management/WP_REGISTRY.md` registers WP-017T before WP-017K.

No product logic, runtime code, DB data, schema, service config, import/parser/evaluator behavior or WP-018 product planning was changed.

## 2. Preflight

- Path: `/opt/jc-coach`
- Branch: `main`
- Git status before: clean
- Latest commits observed:
  - `db85f30 (HEAD -> main) Repair governance entrypoints and document match mode deferral`
  - `6514c80 Diagnose match mode classification limits`
  - `e96864c Repair WP registry governance`
  - `e6b5165 Add root Codex agent contract`
  - `e17f070 (origin/main) Accept post-batch performance with warnings`
  - `dd5f499 Accept post-batch data integrity with warnings`
  - `1b18ce9 Verify repaired pending demo import evaluation`
  - `41a7c5e Repair Steam import recommendation evaluation timing`

## 3. Files Changed

- `docs/CURRENT_STATUS.md`
  - Reason: keep this Hot context file concise enough for every task.
  - Summary: replaced long WP history with current version, lane, active/next WP, promotion status, blockers, accepted limitations, runtime basics, latest known DB SHA and pointers to detail.

- `docs/HANDOFF.md`
  - Reason: make this a new-session bootstrap instead of a full project archive.
  - Summary: retained project identity, Hot context order, current state summary, next safe step, forbidden actions and reporting rules; removed long historical WP narrative.

- `docs/DECISIONS.md`
  - Reason: record current governance/product-process decisions after WP-017S/J/T.
  - Summary: added concise dated decisions for AGENTS/HOT/Warm/Cold policy, out-of-band WP-018 audit naming, match-mode deferral and Steam demo cap.

- `docs/project_management/WP_REGISTRY.md`
  - Reason: register WP-017T and make it a prerequisite before WP-017K.
  - Summary: added WP-017T as a done governance/documentation task with this report path and added it to WP-017K dependencies/current promotion gate.

- `docs/audit/WP_017T_COMPACT_CURRENT_STATUS_HANDOFF_REPORT.md`
  - Reason: required audit report for WP-017T.
  - Summary: records scope, changed files, source-of-truth model, intentional non-changes, next step and checks.

## 4. Current Source-Of-Truth Model

Per-task Hot context:

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/project_management/WP_REGISTRY.md`

New-session Hot context additionally includes:

4. `docs/HANDOFF.md`

Warm context rule: read Warm docs only when the task requires them, and state which files are needed and why before reading them.

Cold/evidence rule: old audit reports, prompts, stage reports and generated data reports are evidence/history only and must not override current control docs.

## 5. What Was Intentionally Not Changed

- No application code changed.
- No DB data or schema changed.
- No service, systemd or nginx config changed.
- No import, parser, evaluator or manual evaluator job ran.
- No product logic changed.
- No `v0.9` promotion was performed.
- No planned WP-018 product block changes were made.
- No archive moves, deletes or renames were performed.
- No `git add`, commit or push was performed.

## 6. Next Recommended Step

Review the WP-017T documentation diff. If accepted, commit the governance documentation changes. Then continue to `WP-017K Real Data Onboarding Promotion to v0.9` only after user/ChatGPT approval.

WP-017K must carry forward WP-017G/H warnings, WP-017J match-mode limitation text, Steam demo cap `1`, root-backed storage warnings and authenticated browser timing limitations.

## 7. Checks

Checks run:

- `git diff --stat`:
  - `docs/CURRENT_STATUS.md`: compacted
  - `docs/DECISIONS.md`: updated
  - `docs/HANDOFF.md`: compacted
  - `docs/project_management/WP_REGISTRY.md`: WP-017T registration/dependency update
  - 4 tracked files changed, 142 insertions and 231 deletions
- `git status --short`:
  - `M docs/CURRENT_STATUS.md`
  - `M docs/DECISIONS.md`
  - `M docs/HANDOFF.md`
  - `M docs/project_management/WP_REGISTRY.md`
  - `?? docs/audit/WP_017T_COMPACT_CURRENT_STATUS_HANDOFF_REPORT.md`
- `python3 scripts/project_gate.py --help`: succeeded; available commands are `preflight`, `changed`, `required-checks` and `postflight`.

These checks were selected because they are read-only and do not mutate production DB, run imports, run parsers, run evaluators or change service state.
