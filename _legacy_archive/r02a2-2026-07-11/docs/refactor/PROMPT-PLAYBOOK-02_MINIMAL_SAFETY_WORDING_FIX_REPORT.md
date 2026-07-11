# PROMPT-PLAYBOOK-02 Minimal Safety Wording Fix Report

## Result

PASS.

`docs/project_management/PROMPT_PLAYBOOK.md` was minimally updated to avoid
overbroad Steam import and post-foundation audit wording while preserving the
current JC Coach safety guardrails.

## Changed files

- `docs/project_management/PROMPT_PLAYBOOK.md`
- `docs/refactor/PROMPT-PLAYBOOK-02_MINIMAL_SAFETY_WORDING_FIX_REPORT.md`

## Fixes applied

- Updated the `STEAM_IMPORT` task type forbidden-actions wording from
  absolute `demo download` language to `unscoped demo download/storage mutation`.
- Updated the `POST_FOUNDATION_AUDIT` task type Required Warm docs wording to
  use current Hot docs, current risk/closure summaries, and only
  task-relevant archived foundation evidence when needed.
- Updated the Audit/Stabilization template to avoid requiring the full
  foundation hardening recovery plan/history by default.

## Checks

- Preflight `git status --short`: clean before edits.
- Preflight branch: `cona`.
- Preflight HEAD: `eebef40807f025fcccf9c07fbe1ebaaf734bad76`.
- `git diff --check`: PASS.
- `git status --short`:

```text
 M docs/project_management/PROMPT_PLAYBOOK.md
?? docs/refactor/PROMPT-PLAYBOOK-02_MINIMAL_SAFETY_WORDING_FIX_REPORT.md
```

## Remaining warnings

- This docs-only task does not authorize JC Forge, Codex Native
  implementation, WP-018 restart, major CS2 product work, public/friends
  readiness, `v1.0`, or DB/schema/import/parser/evaluator/runtime/deploy/
  package work without explicit scope.
- The playbook remains a prompt-template guide, not the root contract.

## Recommended next task

Run a focused documentation QA review of the prompt playbook after any future
post-foundation audit/stabilization prompt updates.
