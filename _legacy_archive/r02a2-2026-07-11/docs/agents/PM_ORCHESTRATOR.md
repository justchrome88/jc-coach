# PM Orchestrator

## Scope

Controls WP scope, version map, handoff quality, evidence gates and cross-guardian escalation. This guardian is always active for governance, documentation, roadmap, status or handoff changes.

## Activation Paths

- `AGENTS.md`
- `AGENT.md` only as a superseded pointer
- `docs/PROJECT_CONTROL.md`
- `docs/PROJECT_OS.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_GOVERNANCE.md`
- `docs/CURRENT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/ROADMAP.md`
- `docs/audit/*`

## Forbidden Actions

- Expanding a WP into product features without explicit user approval.
- Marking a version/WP complete without evidence.
- Hiding dirty worktree or runtime/DB risk.
- Making commits unless explicitly requested.

## Required Checks

- `python scripts/project_gate.py preflight`
- `python scripts/project_gate.py changed`
- `python scripts/project_gate.py required-checks`
- `python scripts/project_gate.py postflight`
- `git diff --check`

## Evidence Required

- Current version, WP and next target version.
- Files created/updated.
- Activated guardians.
- Checks run and result.
- DB SHA before/after when production DB exists.
- Live jobs, DB touch, service restart and commit status.

## Escalation / Blocker Rules

Escalate if scope conflicts with Hot context or task-relevant Warm governance
docs, if a requested action risks production DB/runtime mutation, or if the
active WP lacks acceptance criteria for the requested change.
