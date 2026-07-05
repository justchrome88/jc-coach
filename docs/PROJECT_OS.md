# Project OS

> Status: Historical / superseded as the active Codex entrypoint.
> Do not use this file as current project state.
> Current source of truth: `AGENTS.md`, `docs/CURRENT_STATUS.md`,
> `docs/project_management/WP_REGISTRY.md`.
> For new-session bootstrap, also read `docs/HANDOFF.md`.

Short historical entrypoint for Codex passes or chats.

## Current State

- Current Product Version: see `docs/CURRENT_STATUS.md`.
- Current WP: see `docs/project_management/WP_REGISTRY.md`.
- Next Target Version: see `docs/CURRENT_STATUS.md`.
- Current gate: governance-controlled pass; no product logic or DB mutation without explicit WP authorization.

## Source Of Truth

- Human docs entrypoint: `docs/README.md`
- Human docs index: `docs/project_management/DOCS_INDEX.md`
- Control: `docs/PROJECT_CONTROL.md`
- Current status: `docs/CURRENT_STATUS.md`
- Current milestone: `docs/CURRENT_MILESTONE.md`
- Governance: `docs/PROJECT_GOVERNANCE.md`
- Handoff: `docs/HANDOFF.md`
- Version roadmap: `docs/project_management/VERSION_ROADMAP.md`
- Work package backlog: `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- Acceptance matrix: `docs/project_management/ACCEPTANCE_MATRIX.md`
- Docs map: `docs/project_management/DOCS_MAP.md`
- Testing: `docs/TESTING.md`
- Security: `docs/SECURITY.md`
- Backup/restore: `docs/BACKUP_RESTORE.md`
- Deployment/runtime: `docs/DEPLOYMENT.md`

## Reading Policy

Use the Hot/Warm/Cold context policy in `AGENTS.md`.

Per-task Hot context:

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/project_management/WP_REGISTRY.md`

New-session Hot context additionally includes:

4. `docs/HANDOFF.md`

Warm docs are read only when the task domain requires them. Before reading Warm
docs, state which files are needed and why.

## Guardians

- `PM_ORCHESTRATOR`: WP scope, version map, handoff, gates.
- `DB_GUARDIAN`: DB files, auth persistence, migrations, contamination risk.
- `RUNTIME_GUARDIAN`: FastAPI/web runtime, service freshness, smoke checks.
- `TEST_GUARDIAN`: test isolation and safe verification.
- `IMPORT_GUARDIAN`: Steam/import/demo parser boundaries.
- `METRICS_GUARDIAN`: metric truth, recommendation evidence, AI output truth.
- `UI_COACH_GUARDIAN`: `/coach` UI honesty and read-only page rendering.

## Start A Codex Pass

```bash
git status --short
git log --oneline -12
sha256sum data/cs2_coach.db
systemctl status jc-coach --no-pager
python scripts/project_gate.py preflight
python scripts/project_gate.py changed
python scripts/project_gate.py required-checks
```

Then read the guardian docs activated by the changed paths.

For roadmap context, read:

- `docs/project_management/VERSION_ROADMAP.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/project_management/DOCS_MAP.md`

For human navigation, start with:

- `docs/README.md`
- `docs/project_management/DOCS_INDEX.md`

## Hand Off To A New Chat

Update `docs/HANDOFF.md` when current state, blocker, DB SHA, runtime status or next WP changes. The final report must name files changed, checks run, DB SHA before/after, live jobs run, production DB touched, service restart status and next recommended WP.
