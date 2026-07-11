# Role Card Template

Last updated: 2026-07-06.

## Role Name

Name the role.

## Purpose

State why the role exists.

## When Invoked

List task types or prompt phrases that invoke the role.

## Inputs / Docs It May Read

List Hot context and task-relevant Warm docs. Do not expand Hot context.

## What It Checks

List the checks this role owns.
Include invocation mode and output mode if the role can affect safety or output
length.

## Allowed Actions

List actions the role may take.

## Forbidden Actions

List actions the role must not take.

## Required Output

List the output the next role or user needs.
State when output should be console-only, file-backed or patch-producing.

## Handoff To Other Roles

State what this role passes to other roles.

## Red Flags

List conditions that require stopping, blocking or user approval.

## Related Docs

List related workflow, operating and domain docs.

## How To Modify This Role Later

Changing a role card requires explicit user-approved governance/documentation
scope, `AGENT_WORKFLOW.md` alignment, docs navigation updates and a WP report.
Do not add runtime automation through a role card.

## Future Role Checklist

- Role is necessary and not covered by existing roles.
- User explicitly approved the new role.
- Role card is created under `docs/agents/roles/`.
- `AGENT_WORKFLOW.md` links the role.
- `DOCS_INDEX.md` and `DOCS_MAP.md` are updated.
- WP is registered in `WP_REGISTRY.md`.
- No Hot context expansion.
- No daemon, scheduler, queue, background worker or autonomous runtime.
