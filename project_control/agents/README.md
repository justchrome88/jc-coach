# Agent Roles And Guardians

Last updated: 2026-07-06.

This directory contains two different kinds of guidance.

## Workflow Role Cards

`project_control/agents/roles/` contains repo-native workflow role cards:

- `project_control/agents/roles/PM_ORCHESTRATOR.md`
- `project_control/agents/roles/IMPLEMENTATION_AGENT.md`
- `project_control/agents/roles/QA_REVIEWER.md`
- `project_control/agents/roles/DOCUMENTATION_STEWARD.md`
- `project_control/agents/roles/ROLE_CARD_TEMPLATE.md`

These are Warm role definitions. They do not expand per-task Hot context.
Codex reads a role card only when that role is invoked or the task type requires
it. These roles are not autonomous processes, daemons, schedulers, queues or
runtime automation.

`project_control/agents/AGENT_WORKFLOW.md` remains the workflow router.
It defines invocation modes and output modes, including when long role outputs
should be file-backed instead of console-only.
`project_control/agents/PROJECT_OPERATING_PROTOCOL.md` remains the operating
policy.

## Domain Guardian Docs

`project_control/agents/guardians/*_GUARDIAN.md` files are supporting domain
guardrails. They define safety boundaries for DB, runtime, tests,
import/parser, metrics and UI work.
They remain supporting references and do not replace workflow role cards.

The former supporting PM/domain guardrail and PM role card were merged into
`project_control/agents/roles/PM_ORCHESTRATOR.md`; their originals are archived.

## Adding A New Role

New roles require explicit user approval.

1. Create a role card from `project_control/agents/roles/ROLE_CARD_TEMPLATE.md`.
2. Link it from `project_control/agents/AGENT_WORKFLOW.md`.
3. Update `project_control/manifests/DOCS_MAP.md`.
4. Register the approving WP in `project_control/planning/WP_REGISTRY.md`.
5. Do not create runtime automation unless explicitly approved.
