# PROMPT-PLAYBOOK-01 Create Project Prompt Playbook Report

Task ID: `PROMPT-PLAYBOOK-01_CREATE_PROJECT_PROMPT_PLAYBOOK`

Date: 2026-07-09

Role: Codex Documentation Steward

Mode: `docs-only / prompt-playbook / file-backed`

## Result

`PASS`

Created a simple project Prompt Playbook for future ChatGPT-generated Codex
task prompts for JC Coach. The work stayed docs-only and did not introduce
Codex Native, JC Forge, a new agent system or foundation adapter/core
directories.

## Changed Files

- `docs/project_management/PROMPT_PLAYBOOK.md`
- `docs/HANDOFF.md`
- `docs/refactor/PROMPT-PLAYBOOK-01_CREATE_PROJECT_PROMPT_PLAYBOOK_REPORT.md`

## What Was Created

`docs/project_management/PROMPT_PLAYBOOK.md` now provides:

- Universal rules for future JC Coach Codex prompts.
- A task type router for parser, metrics, recommendation, AI coach, UI, import,
  DB/schema, QA, docs-only, audit/stabilization and release/closure prompts.
- A reusable universal prompt skeleton.
- Focused templates for parser, metrics, recommendation, AI coach quality,
  UI/web, audit/stabilization and release/closure tasks.
- Anti-patterns that future prompts should avoid.

## How Future Prompts Should Use It

Future ChatGPT prompt-generation sessions should read Hot docs first, then use
`docs/project_management/PROMPT_PLAYBOOK.md` as the prompt-template guide when
drafting Codex task prompts. The playbook should help choose task type,
required Warm docs, safety gates, allowed files, forbidden actions, checks and
expected console output.

`docs/HANDOFF.md` now includes a short bootstrap pointer to the playbook after
Hot docs.

## Checks

- Preflight `git status --short`: clean before work.
- Preflight branch: `cona`.
- Preflight HEAD: `47990dcbced40f793d784702577c3e960fb124e0`.
- Read only the requested input docs before editing:
  - `AGENTS.md`
  - `docs/CURRENT_STATUS.md`
  - `docs/HANDOFF.md`
  - `docs/project_management/WP_REGISTRY.md`
  - `docs/refactor/LEAN-DOCS-06_CLOSE_LEAN_DOCS_CLEANUP_REPORT.md`
- `git diff --check`: PASS with no output.
- `git status --short`:

```text
 M docs/HANDOFF.md
?? docs/project_management/PROMPT_PLAYBOOK.md
?? docs/refactor/PROMPT-PLAYBOOK-01_CREATE_PROJECT_PROMPT_PLAYBOOK_REPORT.md
```

## Warnings

- No product code, tests, scripts, tools, data, deploy, DB/schema/uploads/raw
  demo, backup or package/dependency files were changed.
- No live Steam/Valve import, parser job, evaluator job, service restart,
  package install, commit or push was performed.
- The playbook is guidance for future prompt writing only; it does not
  authorize WP-018 restart, major CS2 feature work, JC Forge, Codex Native,
  public/friends readiness or `v1.0` claims.

## Recommended Next Task

`POST-FOUNDATION-01_DEFECT_WARNING_AUDIT_AND_STABILIZATION_PLAN`
