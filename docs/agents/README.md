# Agent Roles And Guardians

Last updated: 2026-07-06.

This directory contains two different kinds of guidance.

## Workflow Role Cards

`docs/agents/roles/` contains repo-native workflow role cards:

- `docs/agents/roles/PM_ORCHESTRATOR.md`
- `docs/agents/roles/IMPLEMENTATION_AGENT.md`
- `docs/agents/roles/QA_REVIEWER.md`
- `docs/agents/roles/DOCUMENTATION_STEWARD.md`
- `docs/agents/roles/ROLE_CARD_TEMPLATE.md`

These are Warm role definitions. They do not expand per-task Hot context.
Codex reads a role card only when that role is invoked or the task type requires
it. These roles are not autonomous processes, daemons, schedulers, queues or
runtime automation.

`docs/project_management/AGENT_WORKFLOW.md` remains the workflow router.
It defines invocation modes and output modes, including when long role outputs
should be file-backed instead of console-only.
`docs/project_management/PROJECT_OPERATING_PROTOCOL.md` remains the operating
policy.

## Domain Guardian Docs

`docs/agents/*_GUARDIAN.md` files are supporting domain guardrails. They define
safety boundaries for DB, runtime, tests, import/parser, metrics and UI work.
They remain supporting references and do not replace workflow role cards.

`docs/agents/PM_ORCHESTRATOR.md` is an existing supporting PM/domain guardrail.
The canonical PM workflow role card is
`docs/agents/roles/PM_ORCHESTRATOR.md`.

## Adding A New Role

New roles require explicit user approval.

1. Create a role card from `docs/agents/roles/ROLE_CARD_TEMPLATE.md`.
2. Link it from `docs/project_management/AGENT_WORKFLOW.md`.
3. Update `docs/project_management/DOCS_INDEX.md` and
   `docs/project_management/DOCS_MAP.md`.
4. Register the approving WP in `docs/project_management/WP_REGISTRY.md`.
5. Do not create runtime automation unless explicitly approved.
